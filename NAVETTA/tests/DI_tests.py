"""
Tests for Master thesis
"""

import cfg
from TestSuite import runTests, SummaryType, TestUtils as TU
import re
import operator as op

def main():
    seqs = cfg.sequences[cfg.hevc_A] + cfg.sequences[cfg.hevc_B]
    in_names = cfg.class_sequence_names[cfg.hevc_A] + cfg.class_sequence_names[cfg.hevc_B]
    ver = 26
    
    dqps = (0, -3, -6, -9)
    base_qp = (22, 27, 32, 37)
    
    outname = "DI_tests_v{}".format(ver)

    # Set shared param
    HSCAL = "1.5X"
    SCAL = "2X"
    SNR = "SNR"

    # Basic init
    skvz_tpg_scal = TU.TestParameterGroup()
    skvz_tpg_scal.add_const_param(version = ver,
                                  input_names = in_names,
                                  inputs = seqs) \
                 .add_param_set(_dqp = dqps,
                                _type = [SNR, SCAL, HSCAL]) \
            #.filter_parameter_group(lambda *, _dqp, _type, **param: True if _type == SNR or _dqp == 0 else False)

    skvz_tpg_sim = skvz_tpg_scal.copy()
    shm_tpg_scal = skvz_tpg_scal.copy()
    shm_tpg_sim = skvz_tpg_scal.copy()

    hscale = (1/1.5, 1)
    scale = (0.5, 1)
    snr_scale = (1, 1)

    name_scaling = {SNR: lambda s: s,
                    SCAL: lambda s: TU.generate_scaled_seq_names(s, scale),
                    HSCAL: lambda s: TU.generate_scaled_seq_names(s, hscale)}
    sim_scaling = {SNR: lambda s: s,
                    SCAL: lambda s: TU.generate_scaled_seq_names(s, (scale[0],)),
                    HSCAL: lambda s: TU.generate_scaled_seq_names(s, (hscale[0],))}
    shm_name_scaling = {SNR: lambda s: ([(seq, seq) for (seq,) in s]),
                        SCAL: lambda s: TU.generate_scaled_seq_names(s, scale),
                        HSCAL: lambda s: TU.generate_scaled_seq_names(s, hscale)}
    
    # Set kvazaar scalable param
    threads = "15"#(4,6,8,10,12,14)
    owf = "2"#(2,4,8,16)
    shared_param = ("--preset", "ultrafast", "--threads", threads, "--owf", owf)

    skvz_tpg_scal.add_const_param(layer_args = shared_param,
                                  retries = 5,
                                  bin_name = cfg.skvz_ver_bin.format(ver))

    #tpg_scal.filter_parameter_group(lambda *, _dqp, _type, **param: False if _type == SNR and _dqp == 0 else True)

    skvz_tpg_scal.set_param_group_transformer(
        TU.transformerFactory(test_name = lambda *, _dqp, _type, **param: "SKVZ_SCAL_{}_DQP{}".format(_type, _dqp),
                              qps = lambda *, _dqp, **param: tuple(zip(base_qp, [bqp + _dqp for bqp in base_qp])),
                              inputs = lambda *, _type, inputs, **param: name_scaling[_type](inputs),
                              layer_args = lambda *, layer_args, **param: (layer_args , layer_args))
        )

    # Set kvazaar simulcast param
    skvz_tpg_sim.add_const_param(bin_name = cfg.skvz_ver_bin.format(ver),
                                 validate = False,
                                 layer_args = shared_param)

    skvz_tpg_sim.set_param_group_transformer(
        TU.transformerFactory(test_name = lambda *, _dqp, _type, **param: "SKVZ_{}_DQP{}".format(_type, _dqp) if _type == SNR else "SKVZ_1/{}".format(_type),
                              qps = lambda *, _dqp, **param: tuple(bqp + _dqp for bqp in base_qp),
                              layer_args = lambda *, layer_args, **param: (layer_args,),
                              inputs = lambda *, inputs, _type, **param: sim_scaling[_type](inputs))
        )

    # Set shm scalable param
    base_conf = cfg.shm_cfg + "encoder_lowdelay_P_scalable.cfg"
    layer_conf = cfg.shm_cfg + "layers.cfg"
    
    shm_tpg_scal.set_param_group_transformer(
        TU.transformerFactory(test_name = lambda *, _dqp, _type, **param: "SHM_SCAL_{}_DQP{}".format(_type, _dqp),
                              qps = lambda *, _dqp, **param: tuple(zip(base_qp, [bqp + _dqp for bqp in base_qp])),
                              inputs = lambda *, _type, inputs, **param: shm_name_scaling[_type](inputs),
                              configs = lambda *, _type, input_names, **param:
                                [ (base_conf, layer_conf, cfg.shm_cfg + seq.split("_")[1] + "-" + _type + ".cfg") for seq in input_names])
        )\
            .filter_parameter_group(lambda *, _dqp, _type, **param: True if _type == SNR or _dqp == 0 else False)\
            .filter_parameter_group(lambda *, _dqp, _type, **param: False if _type == SNR and _dqp == 0 else True)

    # Set shm simulcast param
    shm_tpg_sim.set_param_group_transformer(
        TU.transformerFactory(test_name = lambda *, _dqp, _type, **param: "SHM_{}_DQP{}".format(_type, _dqp) if _type == SNR else "SHM_1/{}".format(_type),
                              qps = lambda *, _dqp, **param: tuple(bqp + _dqp for bqp in base_qp),
                              configs = lambda *, input_names, **param:
                                [ (base_conf, cfg.shm_cfg + seq.split("_")[1] + ".cfg") for seq in input_names],
                              inputs = lambda *, inputs, _type, **param: sim_scaling[_type](inputs),
                              input_layer_scales = lambda *, _type, **param: tuple() if _type == SNR else (1,))
        )\
            .filter_parameter_group(lambda *, _dqp, _type, **param: True if _type == SNR or _dqp == 0 else False)

    #Get tests
    skvz_tests_scal = skvz_tpg_scal.to_skvz_test_instance()
    skvz_tests_sim = skvz_tpg_sim.to_skvz_test_instance()
    shm_tests_scal = shm_tpg_scal.to_shm_test_instance()
    shm_tests_sim = shm_tpg_sim.to_shm_test_instance()

    skvz_combi = TU.generate_combi(skvz_tpg_sim,
                                  combi_cond = TU.combiFactory(
                                      lambda g1, g2: (g1["_type"] == SNR == g2["_type"]) or (g1["_type"] == SNR != g2["_type"] and g1["_dqp"] == 0) or (g2["_type"] == SNR != g1["_type"] and g2["_dqp"] == 0),
                                  _type = lambda t1, t2: -1 if t1 != SNR == t2 else 1 if t1 == SNR != t2 else t1 == t2,
                                  _dqp = lambda d1, d2: True if d2 == d1 == 0 else d2 if d1 == 0 else (-d1 if d2 == 0 else 0)))

    shm_combi = TU.generate_combi(shm_tpg_sim, 
                                  combi_cond = TU.combiFactory(lambda g1, g2: (g1["_type"] == SNR == g2["_type"]) or (g1["_type"] == SNR != g2["_type"] and g1["_dqp"] == 0) or (g2["_type"] == SNR != g1["_type"] and g2["_dqp"] == 0),
                                                               _type = lambda t1, t2: -1 if t1 != SNR == t2 else 1 if t1 == SNR != t2 else t1 == t2,
                                                               _dqp = lambda d1, d2: True if d2 == d1 == 0 else d2 if d1 == 0 else (-d1 if d2 == 0 else 0)))


    skvz_sim_names = TU.get_combi_names(skvz_combi)
    skvz_test_names = TU.get_test_names(skvz_tests_scal) + skvz_sim_names
    shm_sim_names = TU.get_combi_names(shm_combi)
    shm_test_names = TU.get_test_names(shm_tests_scal) + shm_sim_names

    #Make summaries
    summaries = []
    # SKVZ
    summaries.append(
         TU.make_AnchorList_multiAnchor_definition(skvz_test_names,
                                                   global_filter = lambda t: True if "SCAL" in t else False,
                                                   bdbr_anchor_func = TU.anchorFuncFactory_match_layer(
                                                     lambda t: tuple(a for a in skvz_sim_names if (t.split(sep='_')[1] in a) and (t.split(sep='_')[2] in a))),
                                                   bdbr_layer_func = TU.layerFuncFactory([[None, 1],]),
                                                   time_anchor_func = TU.anchorFuncFactory_match_layer(
                                                     lambda t: (None,) + tuple((a,l) if l >= 0 else a for a in skvz_sim_names if (t.split(sep='_')[1] in a) and (t.split(sep='_')[2] in a) for l in [-1, 1])),
                                                   name="SKVZ_LIST")
         )
    # SKVZ param matrix

    # SHM
    summaries.append(
        TU.make_AnchorList_multiAnchor_definition(shm_test_names,
                                                  global_filter = lambda t: True if "SCAL" in t else False,
                                                  bdbr_anchor_func = TU.anchorFuncFactory_match_layer(
                                                    lambda t: tuple(a for a in shm_sim_names if (t.split(sep='_')[1] in a) and (t.split(sep='_')[2] in a))),
                                                  bdbr_layer_func = TU.layerFuncFactory([[None, 1],]),
                                                  time_anchor_func = TU.anchorFuncFactory_match_layer(
                                                    lambda t: (None,) + tuple((a,l) if l >= 0 else a for a in shm_sim_names if (t.split(sep='_')[1] in a) and (t.split(sep='_')[2] in a) for l in [-1, 1])),
                                                  name="SHM_LIST")
                     )
    # SHM vs. SKVZ
    summaries.append(
        TU.make_AnchorList_multiAnchor_definition(skvz_test_names,
                                                global_filter = lambda t: True if "SCAL" in t else False,
                                                bdbr_anchor_func = TU.anchorFuncFactory_match_layer(
                                                    lambda t: tuple(a for a in TU.get_test_names(shm_tests_scal) if (t.split(sep='_')[1] in a) and (t.split(sep='_')[2] in a))),
                                                bdbr_layer_func = TU.layerFuncFactory([[None, 1],]),
                                                time_anchor_func = TU.anchorFuncFactory_match_layer(
                                                    lambda t: (None,) + tuple((a,l) if l >= 0 else a for a in TU.get_test_names(shm_tests_scal) if (t.split(sep='_')[1] in a) and (t.split(sep='_')[2] in a) for l in [-1, 1])),
                                                name="SKVZ_vs_SHM")
        )

    #Run tests
    runTests(tests_scal + tests_sim, outname, *summaries,
             layer_combi = combi)

if __name__ == "__main__":
    print("Execute test file " + __file__)
    main()

