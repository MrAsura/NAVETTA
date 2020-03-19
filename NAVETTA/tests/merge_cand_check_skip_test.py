
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
    version = 3

    outname = r"kvz_merge_cand_check_skip"
    
    bin_vers = [None, r"global_l1", r"global_l2", r"local_neqz", r"local_thresh", *[f"local_thresh_bi_m{m}" for m in range(3)], *[f"local_neqz_bi_m{m}" for m in range(3)]]
    base_bin = f"D:\\bins\\kvz_v{version}.exe"
    shared_param = ("--preset", "ultrafast", "--gop", "8", "-p", "256", "--rd", "1", "--subme", "1", "--pu-depth-intra", "2-3", "--pu-depth-inter", "1-2", "--me-early-termination", "off")
    bipred = [None, r"--bipred"]
    #veryslow = ("--preset", "veryslow")
    #ultrafast = ("--preset", "ultrafast")

    def has_bipred(b):
        return (lambda _, t: ("bi" in t) == b)

    tpg = TU.TestParameterGroup()
    tpg.add_const_param(input_names = seq_names,
                        layer_args = shared_param,
                        inputs = seqs,
                        validate = False,
                        version = version) \
        .add_param_set(_bin_name = bin_vers, _bi = bipred)

    tpg.filter_parameter_group(lambda *, _bin_name, _bi, **_: (not _bi or not _bin_name) or ("bi" in _bin_name))
    tpg.filter_parameter_group(lambda *, _bin_name, _bi, **_: True if (_bi or not _bin_name) else not ("bi" in _bin_name))

    tpg.set_param_group_transformer(TU.transformerFactory(
        bin_name = lambda *, _bin_name, **_: f"D:\\bins\\kvz_{_bin_name}.exe" if _bin_name else base_bin,
        test_name = lambda *, _bin_name, _bi, **_: ((_bin_name if _bin_name else "kvz") + ("_bi" if _bi else "")),
        layer_args = lambda *, layer_args, _bi, **_: (layer_args + ((_bi,) if _bi else tuple()),)))
    
    tests = tpg.to_kvz_test_instance()

    summary = [TU.make_BDBRMatrix_definition(TU.get_test_names(tests), write_bits = False, write_psnr = False),]

    summary.append(TU.make_AnchorList_singleAnchor_definition(bdbr_anchor = "kvz", bdbr_tests = TU.get_test_names(tests), time_anchor="kvz", time_tests=TU.get_test_names(tests), test_filter=has_bipred(False), name="no_bipred_anchor"))
    summary.append(TU.make_AnchorList_singleAnchor_definition(bdbr_anchor = "kvz_bi", bdbr_tests = TU.get_test_names(tests), time_anchor="kvz_bi", time_tests=TU.get_test_names(tests), test_filter=has_bipred(True), name="bipred_anchor"))
    #summary3 = TU.make_AnchorList_singleAnchor_definition("kvz_hexbs", TU.get_test_names(tests), test_filter = lambda _, test: "kvz_tz" not in test, name="hexbs_anchor")
    summary.append(TU.make_CurveChart_definition(TU.get_test_names(tests), filter_func=lambda t: t in ["local_neqz", "local_thresh", "kvz"], name="no_bipred_curve"))
    #summary.append(TU.make_CurveChart_definition(TU.get_test_names(tests), filter_func=lambda t: t in ["local_neqz_bi", "local_thresh_bi", "kvz_bi"], name="bipred_curve"))
    #summary5 = TU.make_CurveChart_definition(TU.get_test_names(tests), filter_func=lambda t: "veryslow" in t, name = "veryslow_curve")
    #summary5["definition"]["charts"].extend([('psnr','rate'),('psnr','time'),('time','rate'),('time','psnr')])

    runTests(tests, outname, *summary)

if __name__ == "__main__":
    print("Execute test file " + __file__)
    main()

