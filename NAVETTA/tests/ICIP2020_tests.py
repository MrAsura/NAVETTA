"""
Tests for ICIP2020 paper
"""

import cfg
from TestSuite import runTests, SummaryType, TestUtils as TU
import re
import operator as op

def main():
    seqs = cfg.sequences[cfg.hevc_A] + cfg.sequences[cfg.hevc_B]
    in_names = cfg.class_sequence_names[cfg.hevc_A] + cfg.class_sequence_names[cfg.hevc_B]
    ver = 24
    
    dqps = (0, -3, -9)
    base_qp = (22, 27, 32, 37)
    
    outname = "shm_ICIP2020_test_v{}".format(ver)

    # Set shared param
    HSCAL = "1.5x"
    SCAL = "2x"
    SNR = "SNR"

    tpg_scal = TU.TestParameterGroup()
    tpg_scal.add_const_param(version = ver,
                             input_names = in_names,
                             inputs = seqs) \
            .add_param_set(_dqp = dqps,
                           _type = [SNR, SCAL, HSCAL]) \
            .filter_parameter_group(lambda *, _dqp, _type, **param: True if _type == SNR or _dqp == 0 else False)

    tpg_sim = tpg_scal.copy()

    # Set scalable param
    hscale = (1/1.5, 1)
    scale = (0.5, 1)
    snr_scale = (1, 1)

    tpg_scal.filter_parameter_group(lambda *, _dqp, _type, **param: False if _type == SNR and _dqp == 0 else True)

    tpg_scal.set_param_group_transformer(TU.transformerFactory(test_name = lambda *, _dqp, _type, **param: "SCAL_{}_DQP{}".format(_type, _dqp),
                                                               qps = lambda *, _dqp, **param: tuple(zip(base_qp, [bqp + _dqp for bqp in base_qp])),
                                                               inputs = lambda *, _type, inputs, **param: ([(seq, seq) for (seq,) in inputs]) if _type == SNR else
                                                                     TU.generate_scaled_seq_names(inputs, scale) if _type == SCAL else
                                                                     TU.generate_scaled_seq_names(inputs, hscale),
                                                               configs = lambda *, _type, input_names, **param: [ (cfg.shm_cfg + "encoder_lowdelay_P_scalable.cfg", cfg.shm_cfg + "layers.cfg", cfg.shm_cfg + seq.split("_")[1] + "-" + _type + ".cfg") for seq in input_names]))

    # Set simulcast param
    #BL = "BL"
    #EL = "EL"
    #tpg_sim.add_param_set(_layer=[BL,EL])

    #tpg_sim.filter_parameter_group(lambda *, _dqp, _layer, **param: True if _layer != BL or _dqp == 0 else False) \
    #       .filter_parameter_group(lambda *, _layer, _type, **param: True if _layer != EL or _type == SNR else False)

    tpg_sim.set_param_group_transformer(TU.transformerFactory(test_name = lambda *, _dqp, _type, **param: "{}_DQP{}".format(_type, _dqp) if _type == SNR else "1÷{}".format(_type),
                                                              qps = lambda *, _dqp, **param: tuple(bqp + _dqp for bqp in base_qp),
                                                              configs = lambda *, input_names, **param: [ (cfg.shm_cfg + "encoder_lowdelay_P_scalable.cfg", cfg.shm_cfg + seq.split("_")[1] + ".cfg") for seq in input_names],
                                                              inputs = lambda *, inputs, _type, **param: inputs if _type == SNR else
                                                              TU.generate_scaled_seq_names(inputs, (scale[0],)) if _type == SCAL else
                                                              TU.generate_scaled_seq_names(inputs, (hscale[0],)),
                                                              input_layer_scales = lambda *, _type, **param: tuple() if _type == SNR else (1,)
                                                             ))


    #Run tests
    tests_scal = tpg_scal.to_shm_test_instance()
    tests_sim = tpg_sim.to_shm_test_instance()
    combi = TU.generate_combi(tpg_sim, combi_cond = TU.combiFactory(lambda g1, g2: (g1["_type"] == SNR == g2["_type"]) or (g1["_type"] == SNR != g2["_type"] and g1["_dqp"] == 0) or (g2["_type"] == SNR != g1["_type"] and g2["_dqp"] == 0),
                                                                    _type = lambda t1, t2: -1 if t1 != SNR == t2 else 1 if t1 == SNR != t2 else t1 == t2,
                                                                    _dqp = lambda d1, d2: True if d2 == d1 == 0 else d2 if d1 == 0 else (-d1 if d2 == 0 else 0)))

    sim_names = TU.get_combi_names(combi)
    test_names = TU.get_test_names(tests_scal) + sim_names
    matrix_summary = TU.make_BDBRMatrix_definition(test_names + TU.get_test_names(tests_sim), write_bdbr = True, write_bits = False, write_psnr = False,
                                                   layering_func = lambda t: (-1,1),#(-1,1) if "SCAL" not in t else (-1,),
                                                   filter_func = lambda t: True if len(t.split('_')) >= 3 or "SCAL" in t else False)

    anchor_summary = TU.make_AnchorList_multiAnchor_definition(test_names,
                                                               global_filter = lambda t: True if "SCAL" in t else False,
                                                               bdbr_anchor_func = TU.anchorFuncFactory_match_layer(
                                                                   lambda t: tuple(a for a in sim_names if (t.split(sep='_')[1] in a) and (t.split(sep='_')[2] in a))),
                                                               bdbr_layer_func = TU.layerFuncFactory([[None, 1],]),
                                                               time_anchor_func = TU.anchorFuncFactory_match_layer(
                                                                   lambda t: (None,) + tuple((a,l) if l >= 0 else a for a in sim_names if (t.split(sep='_')[1] in a) and (t.split(sep='_')[2] in a) for l in [-1, 1])))

    curve_summary1 = TU.make_CurveChart_definition(test_names + TU.get_test_names(tests_sim), filter_func = lambda x: ("2x" in x) or ("SNR_DQP0" == x or "1÷2x" == x))
    curve_summary2 = TU.make_CurveChart_definition(test_names + TU.get_test_names(tests_sim), filter_func = lambda x: ("1.5x" in x) or ("SNR_DQP0" == x or "1÷1.5x" == x))
    curve_summary3 = TU.make_CurveChart_definition(test_names + TU.get_test_names(tests_sim), filter_func = lambda x: ("DQP-3" in x) or ("SNR_DQP0" == x or "SNR_DQP-3" == x))
    curve_summary4 = TU.make_CurveChart_definition(test_names + TU.get_test_names(tests_sim), filter_func = lambda x: ("DQP-9" in x) or ("SNR_DQP0" == x or "SNR_DQP-9" == x))

    summaries = [matrix_summary, anchor_summary, curve_summary1, curve_summary2, curve_summary3, curve_summary4]
    tests = tests_scal + tests_sim

    runTests(tests, outname, *summaries,
             layer_combi = combi)

if __name__ == "__main__":
    print("Execute test file " + __file__)
    main()


