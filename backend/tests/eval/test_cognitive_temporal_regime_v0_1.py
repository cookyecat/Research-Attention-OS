from eval.live.cognitive_temporal_regime_v0_1 import classify_three_checkpoint


def test_stable(): assert classify_three_checkpoint(0,0,0)=='STABLE'
def test_persistent_shift(): assert classify_three_checkpoint(1,1,0)=='PERSISTENT_SHIFT'
def test_transient_return(): assert classify_three_checkpoint(1,0,1)=='TRANSIENT_RETURN'
def test_late_shift(): assert classify_three_checkpoint(0,1,1)=='LATE_SHIFT'
def test_continuing(): assert classify_three_checkpoint(1,1,1)=='CONTINUING_OR_MULTI_REGIME_DRIFT'
def test_indeterminate_single_edge(): assert classify_three_checkpoint(1,0,0)=='INDETERMINATE'
