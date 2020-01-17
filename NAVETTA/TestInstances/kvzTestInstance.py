from .skvzTestInstance import skvzTestInstance
import re
import cfg

class kvzTestInstance(skvzTestInstance):
    """
    Implement the kvazaar test instance class
    Should work the same as skvzTestInstance but with a few changes to the result parsing
    """
    @staticmethod
    def _get_res_folder():
        return r"kvz_res\\"
    
    _res_regex = r"\sProcessed\s(\d+)\sframes,\s+()(\d+)\sbits\sAVG\sPSNR\sY\s(\d+[.,]\d+)\sU\s(\d+[.,]\d+)\sV\s(\d+[.,]\d+)"

    """
    Parse needed values
    """
    @classmethod
    def _parseVals(cls,results,l_tot,ver):
        trgt = {}
        res = results[cls._RES]
        fs = results[cls._FS]
        res_ex = re.search(cls._res_regex, str(res))
        time_ex = re.search(cls._time_regex, str(res))
        lres_ex = {}
        num_layers = 1
        layers = tuple(range(num_layers))
        
        for lid in layers:
            lres_ex[lid] = None
        
        layers = layers + (l_tot,)
        kbs = cls._parseKBS2(res_ex,lres_ex,num_layers,l_tot,fs)
        kb = cls._parseKB2(res_ex,lres_ex,num_layers,l_tot,fs)
        time = cls._parseTime(time_ex,lres_ex,num_layers,l_tot)
        psnr = cls._parsePSNR(res_ex,lres_ex,num_layers,l_tot)
        return (kbs,kb,time,psnr,layers)
