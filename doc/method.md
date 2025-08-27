# Methodology

## USD SOFR Yield Curve
Yield curve is constructed from SOFR O/N from FED, 3M-SOFR future prices below 2 years, and OIS for 2 years and above. 

## BTC/USD Future Curve
Future price is settlement price. Implied yield is computed by: 
$F = S \exp[t(r_{SOFR}-r_{yield})]$
where $F$ is future price, $S$ is spot price, $t$ is year fraction from today to future settlement date, $r_{SOFR}$ is a corresponding zero rate for SOFR, and $r_{yield}$ is the yield to imply.

## BTC/USD Volatility Surface
Implied volatility is computed with put price for strike below future price and call price for strike above future.  
Arbitrage points are detedced for call spread, butterfly, and calendar. These points can be toggled.

## BTC/USD Risk-Neutral Probability
Risk Neutral Probability density function is implied from Breeden-Litzenberger formula:

$\phi(k) = \frac{\partial^2}{\partial k^2}V(S,T,k)$

where $V(S,T,k)$ is undiscounted call/put price (both option types return the same result).  


Because the option price is rounded to USD 5, this disturbes the second derivative and gives noisy density.
To address the issue, the orginal undiscounted option price $\hat{V}(S,T,k)$ is smoothed by minimizing a loss function:  

$L(\{V(k)\};\{\hat{V}(k)\}) = \int dk\frac{1}{2D^2}[\frac{\partial^2}{\partial k^2}V(k)]^2 + \int dk\frac{1}{2s^2}(V(k)-\hat{V}(k))^2$
  
where $s$ is USD5 and $D$ is max value of slope of density function of log-normal density assuming volatility implied from ATM price $V(k=F)$.

The minimization problem is solved after the loss function is discretized along strike.  

The second derivative for the density computation uses discretization of the original strike grid in data because it is dense.  So, interpolation is not used.  For extrapolation, Pareto tails are calibrated to the both sides.


## BTC/USD Moment Analysis
The goal is to predict probability of spot price at future time.  

To do this, we try to predic moments under physical measure from moments under risk-neutral measure using probability in the last section, similarly to [Forecasting swap rate volatility with information from swaptions, A Liu and J Xie, 2023](https://www.bis.org/publ/work1068.pdf).  

Lasso regression is used to link physical moments with risk-neutral moments. However, due to a lack of data points. There is no meaningful result at this moment.  
