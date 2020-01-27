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
    seq_names[cfg.Kimono1] = "Kimono1"
    version = 1

    outname = r"kvz_gop_level_param_selection"
    
    bins = [r"D:\bins\kvz.exe", r"D:\bins\kvz_max.exe", r"D:\bins\kvz_mid.exe", r"D:\bins\kvz_low.exe", r"D:\bins\kvz_xtra.exe"]

    shared_param = ("--gop", "8")
    veryslow = ("--preset", "veryslow")
    ultrafast = ("--preset", "ultrafast")

    tpg = TU.TestParameterGroup()
    tpg.add_const_param(input_names = seq_names,
                        layer_args = shared_param,
                        inputs = seqs,
                        validate = False,
                        version = version) \
        .add_param_set(bin_name = bins,
                       _preset = [ultrafast, veryslow])

    tpg.set_param_group_transformer(TU.transformerFactory(
        test_name = lambda *, bin_name, _preset, **_: bin_name.split('\\')[-1][:-4] + "_" + _preset[1],
        layer_args = lambda *, layer_args, _preset, **_: (_preset + layer_args,)))

    tests = tpg.to_kvz_test_instance()

    summary = TU.make_BDBRMatrix_definition(TU.get_test_names(tests), write_bits = False, write_psnr = False)

    summary2 = TU.make_AnchorList_singleAnchor_definition("kvz_ultrafast", TU.get_test_names(tests), test_filter = lambda _, test: "ultrafast" in test, name="ultrafast_anchor")
    summary3 = TU.make_AnchorList_singleAnchor_definition("kvz_veryslow", TU.get_test_names(tests), test_filter = lambda _, test: "veryslow" in test, name="veryslow_anchor")
    summary4 = TU.make_CurveChart_definition(TU.get_test_names(tests), filter_func=lambda t: "ultrafast" in t, name = "ultrafast_curve")
    summary5 = TU.make_CurveChart_definition(TU.get_test_names(tests), filter_func=lambda t: "veryslow" in t, name = "veryslow_curve")


    runTests(tests, outname, summary, summary2, summary3, summary4, summary5)

if __name__ == "__main__":
    print("Execute test file " + __file__)
    main()
