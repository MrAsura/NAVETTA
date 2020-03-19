

"""
Tests merge cand check skip 
"""

import cfg
from TestSuite import runTests, SummaryType, TestUtils as TU
import re
import operator as op

def main():
    seqs = cfg.sequences
    seq_names = cfg.class_sequence_names
    version = 4

    outname = r"kvz_bframe_constraint"
    
    bin_vers = [None, r"bframe_constr", r"bframe_constr_v2"]
    base_bin = f"D:\\bins\\kvz_v{version}.exe"
    shared_param = ("--preset", "ultrafast", "--gop", "8", "-p", "256", "--rd", "1", "--subme", "1", "--pu-depth-intra", "2-3", "--pu-depth-inter", "1-2", "--me-early-termination", "off", "--bipred")

    tpg = TU.TestParameterGroup()
    tpg.add_const_param(input_names = seq_names,
                        layer_args = shared_param,
                        inputs = seqs,
                        validate = False,
                        version = version) \
        .add_param_set(_bin_name = bin_vers)

    tpg.set_param_group_transformer(TU.transformerFactory(
        bin_name = lambda *, _bin_name, **_: f"D:\\bins\\kvz_{_bin_name}.exe" if _bin_name else base_bin,
        test_name = lambda *, _bin_name, **_: ((_bin_name if _bin_name else "kvz")),
        layer_args = lambda *, layer_args, **_: (layer_args,)))
    
    tests = tpg.to_kvz_test_instance()

    summary = [TU.make_BDBRMatrix_definition(TU.get_test_names(tests), write_bits = False, write_psnr = False),]

    summary.append(TU.make_AnchorList_singleAnchor_definition(bdbr_anchor = "kvz", bdbr_tests = TU.get_test_names(tests), time_anchor="kvz", time_tests=TU.get_test_names(tests)))

    summary.append(TU.make_CurveChart_definition(TU.get_test_names(tests)))


    runTests(tests, outname, *summary)

if __name__ == "__main__":
    print("Execute test file " + __file__)
    main()

