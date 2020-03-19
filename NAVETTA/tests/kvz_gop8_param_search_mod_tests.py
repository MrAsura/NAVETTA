"""
Tests gop8 gop level dependant parameter selection
"""

import cfg
from TestSuite import runTests, SummaryType, TestUtils as TU
import re
import operator as op

def main():
    seqs = cfg.sequences
    seq_names = cfg.class_sequence_names
    version = 2

    outname = r"kvz_gop_level_search_param_selection"
    
    bin_vers = [None, r"TZ1", r"TZ2", r"TZ3", r"F2_2_0", r"F1_1_0", r"F2_2_1", r"F3-1", r"F3-2", r"F2-1", r"F1-1", r"F3-3", r"FF"]
    base_bin = f"D:\\bins\\kvz_v{version}.exe"
    shared_param = ("--preset", "veryslow", "-p", "256", "--transform-skip")
    #veryslow = ("--preset", "veryslow")
    #ultrafast = ("--preset", "ultrafast")

    tpg = TU.TestParameterGroup()
    tpg.add_const_param(input_names = seq_names,
                        layer_args = shared_param,
                        inputs = seqs,
                        validate = False,
                        version = version) \
        .add_param_set(bin_name = bin_vers,
                       _me = ['tz', 'hexbs'])

    tpg.set_param_group_transformer(TU.transformerFactory(
        bin_name = lambda *, bin_name, **_: f"D:\\bins\\kvz_{bin_name}.exe" if bin_name else base_bin,
        test_name = lambda *, bin_name, _me, **_: (bin_name if bin_name else "kvz") + "_" + _me,
        layer_args = lambda *, layer_args, _me, **_: (layer_args + ('--me',_me),)))

    tpg.filter_parameter_group(lambda *, _me, bin_name, **_: bin_name not in base_bin or _me in "tz")\
       .filter_parameter_group(lambda *, _me, bin_name, **_: r"FF" not in bin_name or "hexbs" not in _me)

    tests = tpg.to_kvz_test_instance()

    summary = TU.make_BDBRMatrix_definition(TU.get_test_names(tests), write_bits = False, write_psnr = False)

    summary2 = TU.make_AnchorList_singleAnchor_definition("kvz_tz", TU.get_test_names(tests), test_filter = lambda _, test: "TZ" not in test, name="tz_anchor")
    #summary3 = TU.make_AnchorList_singleAnchor_definition("kvz_hexbs", TU.get_test_names(tests), test_filter = lambda _, test: "kvz_tz" not in test, name="hexbs_anchor")
    summary4 = TU.make_CurveChart_definition(TU.get_test_names(tests), filter_func=lambda t: t in ["F2_2_1_tz", "F2_2_0_tz", "kvz_tz"])
    #summary5 = TU.make_CurveChart_definition(TU.get_test_names(tests), filter_func=lambda t: "veryslow" in t, name = "veryslow_curve")
    #summary5["definition"]["charts"].extend([('psnr','rate'),('psnr','time'),('time','rate'),('time','psnr')])

    runTests(tests, outname, summary, summary2, summary4)

if __name__ == "__main__":
    print("Execute test file " + __file__)
    main()

