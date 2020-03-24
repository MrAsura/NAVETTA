

"""
Check that bitstream doesn't change between versions
"""

import cfg
from TestSuite import runTests, SummaryType, TestUtils as TU
import re
import operator as op

def main():
    seqs = cfg.sequences
    seq_names = cfg.class_sequence_names
    base_v = 5
    new_v = base_v + 1

    outname = f"kvz_conf_check_v{new_v}"
    
    bin_vers = [f"kvz_v{base_v}", f"kvz_v{new_v}"]
    shared_param = ("--preset", "ultrafast")
    depth = [tuple(), ("--pu-depth-inter", "1-2", "--pu-depth-intra", "2-3")]
    gop = [tuple(), ("--gop", "0"), ("--gop", "8")]

    def has_bipred(b):
        return (lambda _, t: ("bi" in t) == b)

    tpg = TU.TestParameterGroup()
    tpg.add_const_param(input_names = seq_names,
                        layer_args = shared_param,
                        inputs = seqs,
                        validate = False,
                        version = new_v) \
        .add_param_set(_bin_name = bin_vers, _depth = depth, _gop = gop)

    tpg.set_param_group_transformer(TU.transformerFactory(
        bin_name = lambda *, _bin_name, **_: cfg.bin_path + _bin_name + ".exe",
        test_name = lambda *, _bin_name, _depth, _gop, **_: _bin_name + ("_depth" if _depth else "") + "_gop" + (_gop[1] if _gop else ""),
        layer_args = lambda *, layer_args, _depth, _gop, **_: ((layer_args + _depth + _gop),)
        ))
    
    tests = tpg.to_kvz_test_instance()

    summary = [TU.make_BDBRMatrix_definition(TU.get_test_names(tests), write_bits = False, write_psnr = False),]

    summary.append(
        TU.make_AnchorList_multiAnchor_definition(TU.get_test_names(tests),
                                                  lambda test: [a for a in TU.get_test_names(tests) if a.split('_')[2:] == test.split('_')[2:] and a.split('_')[1] != test.split('_')[1]],
                                                  lambda test: f"v{new_v}" in test
                                                  )
        )




    runTests(tests, outname, *summary)

if __name__ == "__main__":
    print("Execute test file " + __file__)
    main()

