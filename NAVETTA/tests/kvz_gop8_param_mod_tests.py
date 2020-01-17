"""
Tests gop8 gop level dependant parameter selection
"""

import cfg
from TestSuite import runTests, SummaryType, TestUtils as TU
import re
import operator as op

def main():
    seqs = cfg.sequences
    seq_names = cfg.sequence_names
    version = 1

    outname = r"kvz_gop_level_param_selection"
    
    bins = [r"D:\bins\kvz.exe", r"D:\bins\kvz_max.exe", r"D:\bins\kvz_mid.exe", r"D:\bins\kvz_low.exe"]

    shared_param = ("--preset", "veryslow")

    tpg = TU.TestParameterGroup()
    tpg.add_const_param(input_names = seq_names,
                        layer_args = (shared_param,),
                        inputs = seqs,
                        validate = False,
                        version = version) \
        .add_param_set(bin_name = bins)

    tpg.set_param_group_transformer(TU.transformerFactory(test_name = lambda *, bin_name, **_: bin_name.split('\\')[-1][:-4]))

    tests = tpg.to_kvz_test_instance()

    summary = TU.make_BDBRMatrix_definition(TU.get_test_names(tests), write_bits = False, write_psnr = False)

    summary2 = TU.make_AnchorList_singleAnchor_definition("kvz", TU.get_test_names(tests))

    runTests(tests, outname, summary, summary2)

if __name__ == "__main__":
    print("Execute test file " + __file__)
    main()