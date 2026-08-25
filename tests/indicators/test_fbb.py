import math
from indicators.fbb.calculator import FBBCalculator

def test_hlc3_vwma_std_levels_warmup():
    data=[{'high':2,'low':0,'close':1,'volume':1},{'high':4,'low':2,'close':3,'volume':2},{'high':6,'low':4,'close':5,'volume':3}]
    out=FBBCalculator(length=2,multiplier=3,levels=[1.0]).calculate(data).rows
    assert out[0]['basis'] is None
    assert out[2]['hlc3']==5
    assert out[2]['basis']==(3*2+5*3)/5
    assert round(out[2]['std'],6)==1.0
    assert out[2]['upper_1.000']==out[2]['basis']+3
    assert out[2]['lower_1.000']==out[2]['basis']-3

def test_missing_columns():
    import pytest
    with pytest.raises(ValueError): FBBCalculator(2).calculate([{'high':1}])
