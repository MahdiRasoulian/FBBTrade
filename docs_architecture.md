# Architecture Notes

The application separates indicator calculation, event detection, entry confirmation, risk, proposal delivery, approval, execution validation, and storage. FBB levels are price-location events. The default mean-reversion rejection model is configurable and can later be replaced with continuation logic without modifying the FBB calculator.
