"""Risk: anomaly detection and disposition (US-801, FR-501/506).

The estate begins at Rung 1 of the cold-start ladder (docs/ml/01): explainable rules over
the validated population, no labels required. Every reviewer disposition carries a reason
code and becomes a labelled example — which is what a supervised layer would later train
on. The detectors advise; a human disposes (ML-1).
"""
