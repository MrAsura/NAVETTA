from .TestInstance import TestInstance
import subprocess as sp
from multiprocessing.pool import Pool
import itertools as it
import re
import cfg
import hashlib
import os

def _worker(seq,qp,cmd,outfile,outlog):
    with open(outlog, 'w+') as lf:
        #p = sp.Popen(cmd,stdout=sp.PIPE,stderr=sp.PIPE)
        p = sp.Popen(cmd, stdout=lf, stderr=sp.PIPE)
        res = p.communicate()
        stats = os.stat(outfile)
        #if res[1] is not None and res[0] is None:
        #    raise ValueError(seq,qp,res[1].decode())
        lf.seek(0) #Need to move to start of file to read output
        return (seq,qp,lf.read(),stats.st_size,res[1].decode() if res[1] is not None else "")
        #return (seq,qp,res[0].decode(),stats.st_size,res[1].decode() if res[1] is not None else "")

class shmTestInstance(TestInstance):
    """Test instance class for shm"""

    __CFG = r"-c"
    __BIN = r"-b"
    __INPUT = r"-i{lid}"
    __WIDTH = r"-wdt{lid}"
    __HEIGHT = r"-hgt{lid}"
    __QP = r"-q{lid}"


    __sum_regex = r"SUMMARY\s-{56}\s"
    __i_slice_regex = r"I Slices\s*-{56}\s"
    __layer_regex_format = r"\sL{lid}\s+(\d+)\s+.\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)"
    __tot_stat_regex = r"Bytes written to file:\s+(\d+)\s+\((\d+\.\d+)\s+kbps\)\s+Total Time:\s+(\d+.\d+)\s+sec\."
    __num_layers_regex = r"Total number of layers\s+:\s+(\d+)"

    __RES = r"output"
    __FS = r"file size"
    __ERR = r"errors"
    
    def __init__(self, test_name, configs, inputs = None, input_sizes = [None], input_names = [None], layer_args = (), layer_sizes = [None], input_layer_scales = (), qps = (22, 27, 32, 37), out_name = r'', bin_name = cfg.shm_bin, version=0, **misc):
        self._layer_sizes = layer_sizes
        self._configs = configs
        self._inputs = inputs
        self._qps = qps
        self._layer_args = layer_args

        self._bin_name = bin_name
        self._version = version

        self._results = {}
        self._test_name = test_name

        self._input_layer_scales = input_layer_scales #tuple([1 for i in range(len(configs[0])-1)])
        self._input_sizes = input_sizes

        # Check that if input_names is given, it is the same length as configs. Both inputs and input_names must not be None
        if (input_names is not None and len(input_names) != len(configs)) or (inputs is not None and len(inputs) != len(configs)) or (input_names is None and inputs is None) :
            raise ValueError("Invalid input_names/inputs parameter given")

        self._input_names = {}

        if input_layer_scales:
            round2 = lambda x,base=2: int(base*round(x/base))
            strscale = lambda size,scale: tuple(map(lambda x: str(round2(int(x)*scale)),re.search("_*(\d+)x(\d+)[_.]*",size).group(1,2)))
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

        if len(inputs) != len(self._input_sizes) and input_sizes[0] is not None:
            raise ValueError("inputs and input_sizes should be the same size")
        if len(inputs) != len(self._layer_sizes) and layer_sizes[0] is not None:
            raise ValueError("inputs and layer sizes must be the same size")
        if input_names[0] is not None and len(inputs) != len(input_names):
            raise ValueError("input and input_names need to be the same length")

        for (conf,seq,size,name) in it.zip_longest(configs,inputs,self._layer_sizes,input_names,fillvalue=None):
            if name is not None:
                self._input_names[name] = (conf,seq,size)
            else:
                self._input_names[str(seq)] = (conf,seq,size)

        self._input_names_order = input_names

        # If no outname given use hash as outname so parallel workers don't use the same file
        self._out_name = out_name if out_name else r'out\\' + self._get_fname_hash()

        #return super().__init__(test_name, inputs, input_sizes, layer_args, layer_sizes, input_layer_scales, qps, out_name)

    @staticmethod
    def _get_res_folder():
        return r"shm_res\\"


    def _get_fname_hash(self):
        hasher = hashlib.sha256()
        #hasher.update(str(self._configs).encode())
        #hasher.update(str(self._inputs).encode())
        #hasher.update(str(self._input_names_order).encode())
        #hasher.update(str(self._input_names).encode())
        hasher.update(str(self._bin_name).encode())
        for (name,val) in sorted(self._input_names.items()):
            hasher.update(str(name).encode())
            hasher.update(str(val).encode())
        hasher.update(str(self._qps).encode())
        hasher.update(str(self._layer_args).encode())
        hasher.update(str(self._input_layer_scales).encode())
        hasher.update(str(self._input_sizes).encode())
        return hasher.hexdigest()


    def _run_tests(self):
        runs = {}
        # Build commands
        for (name,(confs,seq,sizes)) in self._input_names.items():
            runs[name] = {}
            for lqp in self._qps:
                if not hasattr(lqp,"__iter__"):
                    lqp = (lqp,)

                cmd = [self._bin_name]
                for conf in confs:
                    cmd.extend([self.__CFG,conf])
                outfile = cfg.results + self._out_name + "_{qp}_{seq}.hevc".format(qp=lqp,seq=name)
                outlog = outfile + r".log"
                cmd.extend([self.__BIN, outfile])
                if seq is not None:
                    for (lid,qp,size) in it.zip_longest(range(len(seq)),lqp,sizes,fillvalue=None):
                        cmd.extend([self.__INPUT.format(lid=lid),seq[lid]])
                        if size is not None:
                            cmd.extend([self.__WIDTH.format(lid=lid),size[0]])
                            cmd.extend([self.__HEIGHT.format(lid=lid),size[1]])
                        if qp is not None:
                            cmd.extend([self.__QP.format(lid=lid),str(qp)])
                        else:
                            cmd.extend([self.__QP.format(lid=lid),str(lqp[0])])

                cmd.extend(self._layer_args)
                runs[name][str(lqp)] = (cmd, outfile, outlog)

        seq_hash_tests_done = {} #Hold the number of test done for each sequence
        print_hash_format = "\t"
        hash_format = lambda seq: "seq{}".format(hash(seq))

        #Callback function for workers
        def cb( res ):
            nonlocal seq_hash_tests_done, self
            (seq,qp,val,fs,err) = res
            # Update printout
            seq_hash_tests_done[hash_format(seq)] += 1
            print(print_hash_format.format(**seq_hash_tests_done),end='\r')
            # Save reuslts
            self._results[seq][qp] = {self.__RES: val, self.__FS: fs, self.__ERR: err}

        def cb_err( *args, **kwargs ):
            print("Error in worker: ", args, *args, **kwargs) 
            
        pool = Pool(processes = 8)
        print("Start running {name} tests for sequences:".format(name=self._test_name))
        # Add test to pool and run in parallel
        line_sep = "\t|"
        for (seq,qps) in runs.items():
            seq_hash_tests_done[hash_format(seq)] = 0
            print_hash_format += "{" + hash_format(seq) + "}" + " of {}\t".format(len(qps.keys()))
            print(line_sep+seq)
            line_sep += "\t|"
            self._results[seq] = {}
            for (qp,(cmd,outfile,outlog)) in qps.items():
                pool.apply_async(_worker,(seq,qp,cmd,outfile,outlog),callback=cb,error_callback=cb_err)
        print(print_hash_format.format(**seq_hash_tests_done),end='\r')
        # Close pool and wait untill everythin is finnished
        pool.close()
        pool.join()
        print()
        print("Tests done.")


    """
    Parse kb/s from test results 
    """
    @staticmethod
    def __parseKBS(res,lres,nl,l_tot):
        vals = {}
        bit_rate = float(res.group(2))
        for lid in range(nl):
            if lres[lid]:
                lbits = lres[lid].group(2)
                vals[lid] = float(lbits)
            else:
                vals[lid] = bit_rate
        vals[l_tot] = bit_rate
        return vals

    """
    Parse kb from test results
    """
    @staticmethod
    def __parseKB(res,lkbs,nl,l_tot):
        vals = {}
        (bits,brate) = res.group(1,2)
        for lid in range(nl):
            vals[lid] = float(bits) * ( lkbs[lid] / float(brate) )
        vals[l_tot] = float(bits)
        return vals


    """
    Parse kb from test results
    """
    @staticmethod
    def __parseKB2(res,lres,nl,l_tot,fs):
        vals = {}
        brate = res.group(2)
        for lid in range(nl):
            vals[lid] = float(fs) * ( float(lres[lid].group(2)) / float(brate) )
        vals[l_tot] = float(fs)
        return vals

    """
    Parse kb from test results
    """
    @staticmethod
    def __parseKBS2(res,lres,nl,l_tot,fs):
        vals = {}
        brate = res.group(2)
        for lid in range(nl):
            frames = float(lres[lid].group(1))
            vals[lid] = float(fs) * ( float(lres[lid].group(2)) / float(brate) ) / float(frames)
        vals[l_tot] = float(fs) / frames
        return vals

    """
    Parse Time
    """
    @staticmethod
    def __parseTime(res,lres,nl,l_tot):
        vals = {}
        ttime = res.group(3)
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
    def __parsePSNR(lres,nl,l_tot):
        vals = {}
        vals[l_tot] = (0.0,0.0,0.0)
        for lid in range(nl):
            if lres[lid]:
                vals[lid] = tuple(map(float,lres[lid].group(3,4,5)))
                vals[l_tot] = tuple(map(lambda x,y: y+x/nl,vals[lid],vals[l_tot]))
            else:
                vals[lid] = (0.0,0.0,0.0)
        return vals

    """
    Parse needed values
    """
    @classmethod
    def __parseVals(cls,results,l_tot):
        trgt = {}
        res = results[cls.__RES]
        fs = results[cls.__FS]
        sum_ex = re.search(cls.__sum_regex, str(res))
        i_ex = re.search(cls.__i_slice_regex, str(res))
        tot_ex = re.search(cls.__tot_stat_regex, str(res))
        lres_ex = {}
        num_layers = int(re.search(cls.__num_layers_regex,str(res)).group(1))
        layers = tuple(range(num_layers))
        for lid in layers:
            lres_ex[lid] = re.search(cls.__layer_regex_format.format(lid=lid), str(res))
        layers = layers + (l_tot,)
        #kbs = cls.__parseKBS(tot_ex,lres_ex,num_layers,l_tot)
        #kb = cls.__parseKB(tot_ex,kbs,num_layers,l_tot)
        kbs = cls.__parseKBS2(tot_ex,lres_ex,num_layers,l_tot,fs)
        kb = cls.__parseKB2(tot_ex,lres_ex,num_layers,l_tot,fs)
        time = cls.__parseTime(tot_ex,lres_ex,num_layers,l_tot)
        psnr = cls.__parsePSNR(lres_ex,num_layers,l_tot)
        return (kbs,kb,time,psnr,layers)
    
    def getInputNames(self):
        return self._input_names_order if self._input_names_order else list(self._input_names.keys())

    def getResults(self, resBuildFunc, l_tot):
        results = {}
        for (seq,qps) in self._results.items():
            for (qp,res) in qps.items():
                (kbs,kb,time,psnr,lids) = type(self).__parseVals(res,l_tot)
                for lid in lids:
                    resBuildFunc(results,seq=seq,qp=qp,lid=lid,kbs=kbs[lid],kb=kb[lid],time=time[lid],psnr=psnr[lid])
        return results
