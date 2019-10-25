"""
Provides functionality to help generate test scripts
"""

import re
import itertools as it
from enum import Enum, auto
from copy import deepcopy
from typing import List, Dict, Tuple, Any, Callable, Union, Iterable, TypeVar, SupportsFloat

from ..TestInstances import skvzTestInstance, shmTestInstance
from .TestSuite import makeLayerCombiName
from .SummaryFactory import create_BDBRMatrix_definition, create_AnchorList_definition


__round2 = lambda x,base=2: int(base * round(x / base))
__strscale = lambda size,scale: "x".join(map(lambda x: str(__round2(int(x) * scale)),re.search("_*(\d+)x(\d+)[_.]*",size).group(1,2)))
__seq_scale = lambda scale, st: (st[0], __strscale(st[1],scale), st[2])
__seq_map = lambda scale, seq: r"{}_{}_{}_zerophase_0.9pi.yuv".format(*__seq_scale(scale,re.search("(.+\\\\.+)_(\d+x\d+)_(\d+)[_.]",seq).group(1,2,3)))
__bl_seq_map = lambda scale: lambda seq: (__seq_map(scale[0], seq[0]),)
__scal_seq_map = lambda scale: lambda seq: (__seq_map(scale[0],seq[0]),) + seq #TODO: Add scaling to el seq?

"""
Generate sequence names for scaled inputs per layer
"""
def generate_scaled_seq_names(seqs: Iterable[Tuple[str]], scales: Iterable[SupportsFloat]) -> List[Tuple[str,...]]:
    return [tuple(__seq_map(scale, seq[0]) if scale != 1 else seq[0] for scale in scales) for seq in seqs]


##### Function templates/factories for filters and transformers #####
"""
Return filter function
"""
def filterFactory() -> Callable[..., bool]:
    pass

"""
Return transformer function
@param param_set_transformer: Take in <parameter_set_name>:<parameter_set_transformer_func> pairs. The transformer func should take in as parameters the whole parameter group and return the transformed parameter set value. If <parameter_set_name> does not exist yet, it is also added to the final parameter_group
@return function that takes in <parameter_set_name>:<parameter_set_value> pairs (i.e. the parameter group) and returns the transformed parameter_group
"""
def transformerFactory(**param_set_transformers: Dict[str,Callable[...,Any]]) -> Callable[..., dict]:
    return (lambda **param_group: {p_set_name: param_set_transformers.get(p_set_name, lambda **pg: pg[p_set_name])(**param_group) for p_set_name in list(param_group.keys()) + list(param_set_transformers.keys())})


"""
Combi function factory for generating a cmp function for combi definition generation. 
@param arbitrary_funcs Pass arbitrary functions that take in dicts and returns a number (gets added to the final sum) or bool (needs to be true for all funcs or groups are not marked as for combination)
@param param_funcs Pass per-parameter (<param_name>:<func>) functions that are evaluated between the two respective parameters of the two groups returns a number (gets added to the final sum) or bool (needs to be true for all funcs or groups are not marked as for combination)
@return a function that returns 0 if groups should not be combined, <0 if groups should be combined and group one should precede group two, and >0 if group two should precede group one.
"""
def combiFactory(*arbitrary_funcs: List[Callable[[dict,dict], Union[int,bool]]], **param_funcs: Dict[str,Callable[[Any,Any], Union[int,bool]]]) -> Callable[[dict, dict], int]:
    def combi_func(group1: dict, group2: dict) -> int:
        final_val = 0
        #Check arbitrary functions
        for func in arbitrary_funcs:
            ret_val = func(group1,group2)
            if ret_val:
                final_val += 0 if isinstance(ret_val, bool) else ret_val
            else:
                return 0
        #Check per-param functions
        for (param, func) in param_funcs.items():
            ret_val = func(group1[param], group2[param])
            if ret_val:
                final_val += 0 if isinstance(ret_val, bool) else ret_val
            else:
                return 0
        if final_val == 0 and group1 != group2:
            raise ValueError("No order defined (ret val 0, but all combi checks pass)")
        return final_val
    return combi_func


"""
@param tpqs should be a list of TestParameterGroups that are used for forming the combi definitions
@param combi_cond a function that takes in two parameter groups and return a true/non-zero value if parameter groups should be combined. In order to enforce an ordering the combi_cond should return a negative value if pg1 < pg2 (i.e. pg1 should be first in the final combi tuple) and vice versa. The function should be f(a,b)=-f(b,a)
@param name_func function that returns the value used for forming identifying the combi tests in TestSuite
Return the combination definition used by TestSuite to combine results.
"""
def generate_combi(*tpqs: List['TestParameterGroup'], combi_cond: Callable[[dict,dict], int], name_func: Callable[...,str] = lambda **p: get_test_names([skvzTestInstance(**p),])[0]) -> List[Tuple[str]]:
    #loop over all tpqs
    tmp_combi = []
    for tpq in tpqs:    
        #Get all parameter groups
        groups_list = tpq.dump()
        
        #collect combis here as [(<combi_group_1>,<combi_group_2>,...),...]
        #tuples
        combi = []
        for cur_group in groups_list:
            cur_group_set = [cur_group,]
            for cmp_group in groups_list:
                if all([combi_cond(cmp_group, cgs) for cgs in cur_group_set if cmp_group != cgs]):
                    cur_group_set.append(cmp_group)
            combi.append(tuple(cur_group_set))

        #Sort combis
        def combi_sort(combis: Tuple[dict,...]) -> Tuple[dict,...]:
            return combis if len(combis) < 2 else combi_sort(tuple((cmp for cmp in combis[1:] if combi_cond(cmp, combis[0]) < 0))) + (combis[0],) + combi_sort(tuple((cmp for cmp in combis[1:] if combi_cond(combis[0], cmp) < 0)))
        
        #transform into final combi definition (sort combis and remove combis with only one group and dublicate groups)
        tmp_combi += [tuple(name_func(**cmb) for cmb in combi_sort(combis)) for combis in combi if len(combis) > 1]
    
        #Remove dublicate elements
    final_combi = []
    for combi in tmp_combi:
        if not combi in final_combi:
            final_combi.append(combi)

    return final_combi


"""
Get combi names from the given combis
@param combi_definition combi definition
@param combi_name_func function used for generating the combi name
@return list of combi names
"""
def get_combi_names(combi_definition: Iterable[Tuple[str]], combi_name_func: Callable[[Iterable[str]],str] = makeLayerCombiName) -> List[str]:
    return [combi_name_func(combi) for combi in combi_definition]


"""
Get test names for given test instances
@param test_instances an iterable of test instances
@return list of test instance names
"""
def get_test_names(test_instances: Iterable[skvzTestInstance]) -> List[str]:
    return [test._test_name for test in test_instances]



"""
make BDBRMatrix definition ()
@param test_names names for tests that are used in the definition
@param layering_func function that takes in test names and outputs layers to be included
@param filter_func optional function for selecting tests from test_names
@param write_* used for selecting what types of results to include
@return a BDBRMatrix definition
"""
def make_BDBRMatrix_definition(test_names: Iterable[str], layering_func: Callable[[str],Tuple[int]] = lambda _: (-1,), filter_func: Callable[[str],bool] = lambda _: True, write_bdbr: bool = True, write_bits: bool = True, write_psnr: bool = True, write_time: bool = True, name: str = "") -> dict:
    layers = {name : layering_func(name) if filter_func(name) else tuple() for name in test_names}
    return create_BDBRMatrix_definition(layers, write_bdbr, write_bits, write_psnr, write_time, name)

T = TypeVar('T')
Layer_func_t = Callable[[T], Iterable[Union[Tuple[str, int], T]]]
Anchor_func_t = Callable[[Union[Tuple[str, int], str]], Iterable[Union[str,None,Tuple[str,int]]]]

"""
make a anchor function that uses the same layer for anchor as the input, but takes in a function which only takes in the test name
"""
def anchorFuncFactory_match_layer(func: Callable[[str], Iterable[Union[str,None,Tuple[str,int]]]]) -> Anchor_func_t:
    return (lambda test: tuple((t, test[1]) if isinstance(test,tuple) and t and not isinstance(t, tuple) else (t[0], test[1]) if isinstance(test,tuple) and isinstance(t, tuple) else t for t in (func(test[0]) if isinstance(test,tuple) else func(test))))


"""
make a layer function that returns a tuple of test-layer-pairs
@param layers a list of layer inds or None if no layer should be added
@param conds list of functions that should return true if matching list of inds (layers[i]<->conds[i]) should be added for given test 
"""
def layerFuncFactory(layers: Iterable[Iterable[Union[int, None]]], conds: Iterable[Callable[[str], bool]] = [lambda _: True,]) -> Layer_func_t:
    return lambda t: tuple((t, l) if l else t for (layer, cond) in zip(layers, conds) if cond(t) for l in layer)

"""
make AnchorList definition using a single anchor for all tests
@param global_anchor/*_anchor name of anchor used for all tests across all the types of tests or the specified types of tests (can override global). None can be specified to get absolute values (not applicable to bdbr). Anchors may be of form (<test_name>,<target_layer>)
@param global_tests/*_tests names of tests to include in all or the specidied types of tests (can override global)
@param test_filter filter anchor-test pairs 
@param layer_func return either input test name or a tuple of (<test_name>,<target_layer>) for tests
"""
def make_AnchorList_singleAnchor_definition(global_anchor: str = None, global_tests: Iterable[str] = None, *, bdbr_anchor: Union[str, Tuple[str, int]] = None, bdbr_tests: Iterable[str] = None, bits_anchor: Union[str, Tuple[str, int]] = None, bits_tests: Iterable[str] = None, psnr_anchor: Union[str, Tuple[str, int]] = None, psnr_tests: Iterable[str] = None, time_anchor: Union[str, Tuple[str, int]] = None, time_tests: Iterable[str] = None, test_filter: Callable[[str, str], bool] = lambda *_: True, layer_func: Layer_func_t = lambda t: t, name: str = "") -> dict:
    #Set global values
    layered_bdbr = layered_bits = layerred_psnr = layered_time = None
    if global_anchor:
        bdbr_anchor = bits_anchor = psnr_anchor = time_anchor = global_anchor
    if global_tests:
        layered_bdbr = layered_bits = layerred_psnr = layered_time = [(test_l, (global_anchor,)) for test in global_tests if test_filter(global_anchor,test) for test_l in layer_func(test)]
    
    #Construct per result type definitions
    if bdbr_tests:
        layered_bdbr = [(test_l, (bdbr_anchor,)) for test in bdbr_tests if test_filter(bdbr_anchor,test) for test_l in layer_func(test)]
    if bdbr_tests:
        layered_bits = [(test_l, (bits_anchor,)) for test in bits_tests if test_filter(bits_anchor,test) for test_l in layer_func(test)]
    if psnr_tests:
        layered_psnr = [(test_l, (psnr_anchor,)) for test in psnr_tests if test_filter(psnr_anchor,test) for test_l in layer_func(test)]
    if time_tests:
        layered_time = [(test_l, (time_anchor,)) for test in time_tests if test_filter(time_anchor,test) for test_l in layer_func(test)]

    return create_AnchorList_definition(bdbr_def = layered_bdbr,
                                        bits_def = layered_bits,
                                        psnr_def = layered_psnr,
                                        time_def = layered_time,
                                        name = name)

"""
Make AnchorList definition with per test anchors
@param test_in test names that are used to generate the definition
@param global_anchor_func/*_anchor_func functions that return the name of anchor used for all tests across all the types of tests or the specified types of tests (can override global). None can be specified to get absolute values (not applicable to bdbr). May also add layer info in case multiple anchors are returned. Returned anchors may contain layer info i.e be of the form (<test_name>,<target_layer>)
@param global_filter/*_filter filter out unwanted tests.
@param global_layer_func/*_layer_func return either input test name or a tuple of (<test_name>,<target_layer>)
"""
def make_AnchorList_multiAnchor_definition(test_in: Iterable[str], global_anchor_func: Anchor_func_t = None, global_filter: Callable[[str], bool] = lambda _: True, global_layer_func: Layer_func_t = lambda t: (t,), *, bdbr_anchor_func: Anchor_func_t = None, bdbr_filter: Callable[[str], bool] = None, bdbr_layer_func: Layer_func_t = None, bits_anchor_func: Anchor_func_t = None, bits_filter: Callable[[str], bool] = None, bits_layer_func: Layer_func_t = None, psnr_anchor_func: Anchor_func_t = None, psnr_filter: Callable[[str], bool] = None, psnr_layer_func: Layer_func_t = None, time_anchor_func: Anchor_func_t = None, time_filter: Callable[[str], bool] = None, time_layer_func: Layer_func_t = None) -> dict:
    layered_bdbr = layered_bits = layered_psnr = layered_time = None
    
    if global_anchor_func:
        bdbr_anchor_func = bdbr_anchor_func if bdbr_anchor_func else global_anchor_func
        bits_anchor_func = bits_anchor_func if bits_anchor_func else global_anchor_func
        psnr_anchor_func = psnr_anchor_func if psnr_anchor_func else global_anchor_func
        time_anchor_func = time_anchor_func if time_anchor_func else global_anchor_func

    if global_filter:
        bdbr_filter = bdbr_filter if bdbr_filter else global_filter
        bits_filter = bits_filter if bits_filter else global_filter
        psnr_filter = psnr_filter if psnr_filter else global_filter
        time_filter = time_filter if time_filter else global_filter

    if global_layer_func:
        bdbr_layer_func = bdbr_layer_func if bdbr_layer_func else global_layer_func
        bits_layer_func = bits_layer_func if bits_layer_func else global_layer_func
        psnr_layer_func = psnr_layer_func if psnr_layer_func else global_layer_func
        time_layer_func = time_layer_func if time_layer_func else global_layer_func
    
    #Construct per result type definitions
    if bdbr_anchor_func:
        layered_bdbr = [(test_l, tuple(anchor for anchor in bdbr_anchor_func(test_l))) for test in test_in if bdbr_filter(test) for test_l in bdbr_layer_func(test)]
    if bits_anchor_func:
        layered_bits = [(test_l, tuple(anchor for anchor in bits_anchor_func(test_l))) for test in test_in if bits_filter(test) for test_l in bits_layer_func(test)]
    if psnr_anchor_func:
        layered_psnr = [(test_l, tuple(anchor for anchor in psnr_anchor_func(test_l))) for test in test_in if psnr_filter(test) for test_l in psnr_layer_func(test)]
    if time_anchor_func:
        layered_time = [(test_l, tuple(anchor for anchor in time_anchor_func(test_l))) for test in test_in if time_filter(test) for test_l in time_layer_func(test)]

    return create_AnchorList_definition(bdbr_def = layered_bdbr,
                                        bits_def = layered_bits,
                                        psnr_def = layered_psnr,
                                        time_def = layered_time)


"""
Define types for parameter sets that defines the behaviour of adding parameter sets
"""
class _ParamSetType(Enum):
    CONST = auto()
    MULTI = auto()

"""
Class for managing test parameters
    
Takes in parameter sets and generates parameter groups so that each possible parameter combination amongst the parameter sets exist 
"""
class TestParameterGroup:

    __round2 = lambda x,base=2: int(base*round(x/base))
    __strscale = lambda size,scale: "x".join(map(lambda x: str(__round2(int(x)*scale)),re.search("_*(\d+)x(\d+)[_.]*",size).group(1,2)))
    __seq_scale = lambda scale, st: (st[0], _strscale(st[1],scale), st[2])
    __ctc_seq_map = lambda scale, seq, mod: r"{}_{}_{}_{}.yuv".format( *__seq_scale(scale,re.search("(.+\\\\.+)_(\d+x\d+)_(\d+)[_.]",seq).group(1,2,3)), mod )


        
    def __init__(self) -> None:

        self._parameter_sets = {}
        #self._parameter_groups = []
        self._filters = []
        self._transformer = lambda **in_param: in_param


    """
    Return the cartesian product of all the parameter sets
    @return A list of tuples where each tuple contains one item from each parameter set 
    """
    def _cartesian_product(*param_sets: List[Tuple[str,List[Any]]]) -> list:
        #Transform each parameter set to [...,(<set name>, <set param #n>),(<set name>, <set param #n+1>),...] etc.
        flat_param = [[(param_set_name, param) for param in param_list] for param_set_name, param_list in param_sets]
        return it.product(*flat_param)

    
    """
    Add Parameters of the given type
    """
    def _add_param(self, type: _ParamSetType, name_param: Dict[str,Any]) -> 'TestParameterGroup':

        for name, param_set in name_param.items():
            if name not in self._parameter_sets:
                self._parameter_sets[name] = (type, param_set)
            else:
                raise ValueError(f"Parameter set '{name}' already exists.")

        return self

    """
    Add new parameter set. Each value in the given param_set is used when generating parameter groups, so that all parameter set value combinations exist in the parameter groups
    @param name_param: take in any number of {name : param_set} pairs
    @return self
    """
    def add_param_set(self, **name_param) -> 'TestParameterGroup':
        return self._add_param(_ParamSetType.MULTI, name_param)

    """
    Add parameter shared by all parameter groups that contains only one value
    @name_param take in any number of {name : param} pairs
    @return self
    """
    def add_const_param(self, **name_param) -> 'TestParameterGroup':
        return self._add_param(_ParamSetType.CONST, name_param)

    """
    Filter out all parameter groups that do not satisfy the given filter function
    @filter function that takes in as parameters all parameter sets and returns a boolean value
    """
    def filter_parameter_group(self, filter: Callable[..., bool]) -> 'TestParameterGroup':
        self._filters.append(filter)
        return self


    """
    Set function that is 
    @return self
    """
    def set_param_group_transformer(self, func: Callable[..., dict]) -> 'TestParameterGroup':
        self._transformer = func
        return self

    """
    Apply filters in self._filters to the given parameter group
    @param param_group contain one group of parameters to test
    @return true if param_group 
    """
    def _apply_filters(self, param_group):
        return all(filt(**param_group) for filt in self._filters)

    """
    Return list of dicts containing the parameter groups that have been added
    """
    def dump(self) -> List[dict]:
        parameter_groups = []

        #Generate parameter groups
        const_params = {name : val for (name, (_, val)) in filter(lambda p_set: p_set[1][0] == _ParamSetType.CONST, self._parameter_sets.items())}
        multi_params = [(name, val) for (name, (_, val)) in filter(lambda p_set: p_set[1][0] == _ParamSetType.MULTI, self._parameter_sets.items())]

        for m_param_group in TestParameterGroup._cartesian_product(*multi_params):
            parameter_groups.append(self._transformer(**const_params, **dict(m_param_group)))

        #Filter the parameter groups before returning
        return [group for group in parameter_groups if self._apply_filters(group)]

    """
    Return a list of skvzTestInstances
    """
    def to_skvz_test_instance(self) -> List[skvzTestInstance]:
        return [skvzTestInstance(**param) for param in self.dump()]

    """
    Return a list of shmTestInstances
    """
    def to_shm_test_instance(self) -> List[shmTestInstance]:
        return [shmTestInstance(**param) for param in self.dump()]



    """
    Return a deep copy the parameter group
    """
    def copy(self) -> 'TestParameterGroup':
        new_pg = TestParameterGroup()
        new_pg._parameter_sets = deepcopy(self._parameter_sets)
        #new_pg._parameter_groups = deepcopy(self._parameter_groups)
        new_pg._filters = deepcopy(self._filters)
        new_pg._transformer = deepcopy(self._transformer)
        return new_pg

