import abc
import cfg
import json
from pathlib import Path

class TestInstance(abc.ABC):
    """Abstract base class that defines the interface for test instances"""

    """
    Create a test instance object
    @param inputs: Specify input files for each input. Can be a list of input sets for several sequences. Same parameter will be used for each input set.
    @param input_sizes: Specify sizes for each input (if not in filename)
    @param input_names: Specify a user given name for inputs that will be used to identify sequences that should be the same
    @param layer_args: Specify parameters not give as separate args (iterable with an element for each layer)
    @param layer_sizes: Specify layer sizes (iterable with an element for each layer). Gets overwriten if scales is given
    @param input_layer_scales: Set layer Sizes as input sizes scaled by given values
    @param qps: Qp values for which the test is run
    @param test_name: A name for the test instance
    @param out_name: Name for the output files
    @param bin_name: Specify the binary used for encoding
    @param version: Specify binary version
    @param misc: Optional parameters for inherited classes to implement encoder specific parameters 
    @return self object
    """
    @abc.abstractmethod
    def __init__(self, test_name, inputs, input_sizes=[()], input_names=[()], layer_args=(), layer_sizes=[()], input_layer_scales=(), qps=(22, 27, 32, 37), out_name=r"out\\out", bin_name="", version=0, **misc):
        self._results = {}
        pass

    """
    Folder to store results
    """
    @staticmethod
    @abc.abstractmethod
    def _get_res_folder():
       return str()

    """
    Get the hash filename used for storing results
    """
    @abc.abstractmethod
    def _get_fname_hash(self):
        pass
    
    """
    Save results to file
    """
    def _save_results(self):
        fpath = Path(cfg.results + self._get_res_folder() + self._get_fname_hash())
        if not fpath.parent.exists():
            fpath.parent.mkdir()
        file = fpath.open(mode='w')
        json.dump(self._results,file,indent=2)
        file.close()

    """
    Load results from file
    """
    def _load_results(self,input_res=False):
        if input_res:
            hash = input("Hash for {}: ".format(self._test_name))
            file = open(cfg.results + self._get_res_folder() + hash, mode = 'r')
        else:
            file = open(cfg.results + self._get_res_folder() + self._get_fname_hash(),mode = 'r')
        self._results = json.load(file)
        file.close()

    """
    Check if the result file for the current test exist
    """
    def _results_exist(self):
        res_file = Path(cfg.results + self._get_res_folder() + self._get_fname_hash())
        return res_file.is_file()

    """
    Function that executes the actual tests
    """
    @abc.abstractmethod
    def _run_tests(self):
        pass

    """
    Execute the tests.
    @param print_out: A string that is printed if the tests are run again
    """
    def run(self, print_out = "", input_res = False):
        #Check if there exists results for current parameters already
        if self._results_exist() or input_res:
            self._load_results(input_res)
        else:
            #Need to run tests again
            print(print_out, end='')
            self._run_tests()
            self._save_results()
            print("Results saved.")

    """
    Return a list with the names of the inputs for this test
    """
    @abc.abstractmethod
    def getInputNames(self):
        pass

    """
    Return results of tests
    @param resBuildFunc: function that builds the result dict when given values (kbs,kb,time,psnr,seq,lid,scale)
    @param l_tot: identifier used for summary layer
    @return a dict with parsed results
    """
    @abc.abstractmethod
    def getResults(self, resBuildFunc, l_tot):
        pass




