from .TestInstance import TestInstance
import subprocess as sp
import itertools as it
import re
import cfg
import hashlib
import os

class skvzTestInstance(TestInstance):
    """Implements the kvazaar test instance class"""
        
    __LAYER = "--layer"
    __LAYER_RES = "--layer-res"
    __QP = "--qp"
    __INPUT = "--input"
    __INPUT_RES = "--input-res"
    __OUTPUT = "--output"
    __DEBUG = "--debug"

    __RES = r"output"
    __FS = r"file size"

    """
    Create a test instance object
    @param inputs: Specify input files for each input. Can be a list of input sets for several sequences. Same parameter will be used for each input set.
    @param input_sizes: Specify sizes for each input (if not in filename)
    @param layer_args: Specify parameters not give as separate args (iterable with an element for each layer)
    @param layer_sizes: Specify layer sizes (iterable with an element for each layer). Gets overwriten if scales is given
    @param input_layer_scales: Set layer Sizes as input sizes scaled by given values
    @param qps: Qp values for which the test is run. Either a single value used for all layers or a seperate value for each layer
    @param test_name: A name for the test instance
    @param out_name: Name for the output files
    @return self object
    """
    def __init__(self, test_name, inputs, input_sizes=[None], input_names=[None], layer_args=(), layer_sizes=[None], input_layer_scales=(), qps=(22, 27, 32, 37), out_name=r"", bin_name=cfg.skvz_bin, version=0, **misc):
        self._layer_sizes = layer_sizes
        self._layer_args = layer_args
        self._inputs = inputs
        self._input_sizes = input_sizes
        self._input_layer_scales = input_layer_scales

        self._bin_name = bin_name

        self._qps = qps
        self._num_layers = max(len(layer_sizes),len(layer_args))
        
        self._version = version

        self._validate = True
        self._retries = 1

        if "validate" in misc:
            self._validate = misc["validate"]
        if "retries" in misc:
            self._retries = misc["retries"]

        # Check that qps is valid
        if len(qps) != 4:
            raise ValueError("Need exactly four qp values to test to be able to calculate bdrate")
        for qp in qps:
            if hasattr(qp,"__iter__"):
                if len(qp) != self._num_layers:
                    raise ValueError("Need to have the same number of layer qps and layers")

        self._test_name = test_name
        if not test_name:
            self._test_name = inputs[0]

        if input_layer_scales:
            round2 = lambda x,base=2: int(base*round(x/base))
            strscale = lambda size,scale: "x".join(map(lambda x: str(round2(int(x)*scale)),re.search("_*(\d+)x(\d+)[_.]*",size).group(1,2)))
            self._layer_sizes = []
            for (input_set,input_set_sizes) in it.zip_longest(inputs,input_sizes,fillvalue=tuple()):
                insizes = input_set_sizes
                fval = 1
                if not input_set_sizes:
                    #Get sizes from the given inputs
                    insizes = input_set
                    fval = input_set[-1] if len(input_set) < len(input_layer_scales) else 1
                else:
                    fval =  input_set_sizes[-1] if len(input_set) < len(input_layer_scales) else 1
                self._layer_sizes.append( tuple( strscale(size,scale) for (scale,size) in it.zip_longest(input_layer_scales,insizes,fillvalue = fval) ) )
        
        self._input_names = {}
        # Build input_name
        if len(inputs) != len(self._input_sizes) and input_sizes[0] is not None:
            raise ValueError("inputs and input_sizes should be the same size")
        if len(inputs) != len(self._layer_sizes) and layer_sizes[0] is not None:
            raise ValueError("inputs and layer sizes must be the same size")
        if input_names[0] is not None and len(inputs) != len(input_names):
            raise ValueError("input and input_names need to be the same length")

        for (inp,size,name) in it.zip_longest(inputs,self._layer_sizes,input_names,fillvalue=None):
            if name is not None:
                self._input_names[name] = (inp,size if size else [None])
            else:
                self._input_names[str(inp)] = (inp,size if size else [None])

        self._input_names_order = input_names

        #Will contain the execution results
        self._results = {}

        # If no outname given use hash as outname so parallel workers don't use the same file
        self._out_name = out_name if out_name else r'out\\' + self._get_fname_hash()

        #return self

    @staticmethod
    def _get_res_folder():
        return r"skvz_res\\"


    def _get_fname_hash(self):
        hasher = hashlib.sha256()
        #hasher.update(str(self._layer_sizes).encode())
        #hasher.update(str(self._inputs).encode())
        #hasher.update(str(self._input_names).encode())
        #hasher.update(str(self._input_names_order).encode())
        hasher.update(str(self._bin_name).encode())
        for (name,val) in sorted(self._input_names.items()):
            hasher.update(str(name).encode())
            hasher.update(str(val).encode())
        hasher.update(str(self._qps).encode())
        hasher.update(str(self._layer_args).encode())
        hasher.update(str(self._input_sizes).encode())
        hasher.update(str(self._input_layer_scales).encode())
        
        return hasher.hexdigest()

    def _run_tests(self):
        runs = {}
        for (name,(seqs,sizes)) in self._input_names.items():
            seq_runs = {}
            for lqp in self._qps:
                if not hasattr(lqp,"__iter__"):
                    lqp = (lqp,)

                cmd = [self._bin_name]
                for (l,l_res,l_arg,qp,seq) in it.zip_longest([None] + [self.__LAYER] * (self._num_layers - 1),sizes,self._layer_args,lqp,seqs,fillvalue=None):
                    if l is not None:
                        cmd.append(l)
                    if l_arg is not None:
                        cmd.extend(l_arg)
                    if l_res is not None:
                        cmd.extend([self.__LAYER_RES,l_res])
                    if qp is not None:
                        cmd.extend([self.__QP,str(qp)])
                    else:
                        cmd.extend([self.__QP,str(lqp[0])])
                    if seq is not None:
                        cmd.extend([self.__INPUT,cfg.sequence_path + seq])

                outfile = cfg.results + self._out_name + "_{qp}_{seq}.hevc".format(qp=lqp,seq=name)
                outlog = outfile + r".log"
                cmd.extend([self.__OUTPUT, outfile])    
                seq_runs[str(lqp)] = (cmd,outfile,outlog)
            runs[name] = seq_runs
   
        print("Running test {}".format(self._test_name))
        for (seq,qps) in runs.items():
            print("  Sequence: {}".format(seq))
            self._results[seq] = {}
            i = 0
            print("    {} of {} runs complete.\r".format(i,len(qps.keys())),end='')
            for (qp,(cmd,outfile,outlog)) in qps.items():
                with open(outlog,'w+',) as lf:
                    #print(cmd)
                    p = sp.Popen(cmd,stdout=sp.DEVNULL,stderr=lf)#sp.PIPE)
                    out = p.communicate()

                    #Validate output
                    is_valid = True
                    if self._validate:
                        retries = self._retries
                        while True:
                            v = sp.Popen([cfg.decoder_bin, "-b", outfile, "-lid", "-1"], stdout=sp.DEVNULL, stderr=sp.DEVNULL) #Attempt to decode
                            if v.wait():
                                is_valid = False
                                #Decoding failed try again or fail
                                if retries <= 0:
                                    break
                                lf.seek(0)
                                p = sp.Popen(cmd, stdout=sp.DEVNULL, stderr=lf)
                                p.communicate()
                                retries -= 1
                            else:
                                is_valid = True
                                break

                    if not is_valid:
                        print("Test {} failed to decode in sequence {} with qp {}.".format(self._out_name, seq, qp))
                        #continue
                    #print("_________________________out_____________________")
                    #print(out)
                    stats = os.stat(outfile)
                    #self._results[seq][qp] = {self.__RES: out[1].decode(), self.__FS: stats.st_size}
                    lf.seek(0) #Need to move to start of file to read output
                    self._results[seq][qp] = {self.__RES: lf.read(), self.__FS: stats.st_size}
                    i = i + 1
                    print("    {} of {} runs complete.\r".format(i,len(qps.keys())),end='')
            #print("")

    __res_regex = r"\sProcessed\s(\d+)\sframes\sover\s(\d+)\slayer\(s\),\s*(\d+)\sbits\sAVG\sPSNR:\s(\d+[.,]\d+)\s(\d+[.,]\d+)\s(\d+[.,]\d+)"
    __lres_regex_format = r"\s\sLayer\s{lid}:\s*(\d+)\sbits,\sAVG\sPSNR:\s(\d+[.,]\d+)\s(\d+[.,]\d+)\s(\d+[.,]\d+)"
    __time_regex = r"\sEncoding\stime:\s(\d+.\d+)\ss."

    #Version 5+ res regex
    __res_regex_v5 = r"\sProcessed\s(\d+)\sframes\sover\s(\d+)\slayer\(s\),\s*(\d+)\sbits\sAVG\sPSNR\sY\s(\d+[.,]\d+)\sU\s(\d+[.,]\d+)\sV\s(\d+[.,]\d+)"
    __lres_regex_v5_format = r"\s\sLayer\s{lid}:\s*(\d+)\sbits,\sAVG\sPSNR\sY\s(\d+[.,]\d+)\sU\s(\d+[.,]\d+)\sV\s(\d+[.,]\d+)"

    """
    Parse kb/s from test results 
    """
    @staticmethod
    def __parseKBS(res,lres,nl,l_tot):
        vals = {}
        (frames,bits) = res.group(1,3)
        lframes = int(frames)/nl
        for lid in range(nl):
            if lres[lid]:
                lbits = lres[lid].group(1)
                vals[lid] = float(lbits)#/float(lframes)
            else:
                vals[lid] = float(bits)#/float(frames)
        vals[l_tot] = float(bits)#/float(frames)
        return vals

    """
    Parse kb from test results
    """
    @staticmethod
    def __parseKB(res,lres,nl,l_tot):
        vals = {}
        bits = res.group(3)
        for lid in range(nl):
            if lres[lid]:
                lbits = lres[lid].group(1)
                vals[lid] = float(lbits)
            else:
                vals[lid] = float(bits)
        vals[l_tot] = float(bits)
        return vals

    """
    Parse kb from test results
    """
    @staticmethod
    def __parseKB2(res,lres,nl,l_tot,fs):
        vals = {}
        bits = res.group(3)
        for lid in range(nl):
            if lres[lid]:
                lbits = lres[lid].group(1)
                vals[lid] = float(fs) * ( float(lbits) / float(bits) )
            else:
                vals[lid] = float(fs)
        vals[l_tot] = float(fs)
        return vals

    """
    Parse kb from test results
    """
    @staticmethod
    def __parseKBS2(res,lres,nl,l_tot,fs):
        vals = {}
        bits = res.group(3)
        frames = int(res.group(1))
        for lid in range(nl):
            if lres[lid]:
                lbits = lres[lid].group(1)
                vals[lid] = float(fs) * ( float(lbits) / float(bits) ) / frames
            else:
                vals[lid] = float(fs) / frames
        vals[l_tot] = float(fs) / frames
        return vals

    """
    Parse Time
    """
    @staticmethod
    def __parseTime(res,lres,nl,l_tot):
        vals = {}
        ttime = res.group(1)
        for lid in range(nl):
            if lres[lid]:
                ltime = ttime#lres[lid].group(6)
                vals[lid] = float(ltime)
            else:
                vals[lid] = float(ttime)
        vals[l_tot] = float(ttime)
        return vals

    """
    Parse psnr from test results
    """
    @staticmethod
    def __parsePSNR(res,lres,nl,l_tot):
        vals = {}
        for lid in range(nl):
            if lres[lid]:
                vals[lid] = lres[lid].group(2,3,4)
            else:
                vals[lid] = res.group(4,5,6)
        vals[l_tot] = res.group(4,5,6)
        return vals

    """
    Parse needed values
    """
    @classmethod
    def __parseVals(cls,results,l_tot,ver):
        trgt = {}
        res = results[cls.__RES]
        fs = results[cls.__FS]
        if ver <= 4:
            res_ex = re.search(cls.__res_regex, str(res))
        else:
            res_ex = re.search(cls.__res_regex_v5, str(res))
        time_ex = re.search(cls.__time_regex, str(res))
        lres_ex = {}
        num_layers = int(res_ex.group(2))
        layers = tuple(range(num_layers))
        for lid in layers:
            if ver <= 4:
                lres_ex[lid] = re.search(cls.__lres_regex_format.format(lid=lid), str(res))
            else:
                lres_ex[lid] = re.search(cls.__lres_regex_v5_format.format(lid=lid), str(res))
        layers = layers + (l_tot,)
        #kbs = cls.__parseKBS(res_ex,lres_ex,num_layers,l_tot)
        #kb = cls.__parseKB(res_ex,lres_ex,num_layers,l_tot)
        kbs = cls.__parseKBS2(res_ex,lres_ex,num_layers,l_tot,fs)
        kb = cls.__parseKB2(res_ex,lres_ex,num_layers,l_tot,fs)
        time = cls.__parseTime(time_ex,lres_ex,num_layers,l_tot)
        psnr = cls.__parsePSNR(res_ex,lres_ex,num_layers,l_tot)
        return (kbs,kb,time,psnr,layers)


    def getInputNames(self):
        return self._input_names_order if self._input_names_order else list(self._input_names.keys())

    """
    Return a dict containing the test results
    """
    def getResults(self, resBuildFunc, l_tot=-1):
        results = {}
        for (seq,qps) in self._results.items():
            for (qp,res) in qps.items():
                (kbs,kb,time,psnr,lids) = type(self).__parseVals(res,l_tot,self._version)
                for lid in lids:
                    resBuildFunc(results,seq=seq,qp=qp,lid=lid,kbs=kbs[lid],kb=kb[lid],time=time[lid],psnr=psnr[lid])
        return results
