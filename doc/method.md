# Methodology
Here, I minimize description of standard formula we can find in many textbooks. Rather, I focus on some items specific to this analysis.

## USD SOFR Yield Curve
Yield curve is constructed from SOFR O/N from FED, 3M-SOFR future prices below 2 years, and OIS for 2 years and above. 

## BTC/USD Future Curve
Future price is settlement price. Implied yield is computed by: 
$F = S_0 \exp[t(r_{SOFR}-r_{yield})]$
where $F$ is future price, $S_0$ is spot price, $t$ is year fraction from today to future settlement date, $r_{SOFR}$ is a corresponding zero rate for SOFR, and $r_{yield}$ is the yield to imply.

## BTC/USD Volatility Surface
Implied volatility is computed with put price for strike below future price and call price for strike above future.  
Arbitrage points are detedced for call spread, butterfly, and calendar. These points can be toggled.

### Estimattion of future values and discount factors from a list of option quotes
One may think of using the future values from quotes of BTC/USD futures, and discount factor from SOFR curve.  
However, we choose to imply both from a list of option quotes because of  
1. Discounting curve may be different from SOFR curve. Data source does not specify which discounting is used. Margin is [computed by SPAN model](https://www.cmegroup.com/trading/cryptocurrency-indices/cme-options-bitcoin-futures-frequently-asked-questions.html) which considers possible price changes for a given liquidation period, therefore not 100% collateralized. Therefore, the discounting is not the same as SOFR which assumes "sucured" funding.
2. Even if SOFR discounting were used, time nodes in data would have been different from nodes of option expiries. Then, choice of time interpolation would have disturbed the implied volatility calculation, which is not ideal.  

Now, we estimate future values and discount factors from a list of option quotes.  
For a particular expiry date of option $T_o$ and end date of future $T_f$, we have a list of quotes of call $C_i$ cand put $P_i$ prices for strike $K_i$.  
Put-call parity computes a compbination of future value $F_{T_f}$ and discount factor $DF_{T_o}$:  
$C_i - P_i = DF_{T_o} (F_{T_f} - K_i)$  
If we define $a = -DF_{T_o}$ and $b = DF_{T_o} \cdot F_{T_f}$, then  
$C_i - P_i = a K_i + b$  
We can estimate $a$ and $b$ using a simple linear regression. After the estimation of $a$ and $b$, we can compute future value and discount factor:  
$F_{T_f} = - \frac{b}{a}$  
$DF_{T_o} = -a$  
  
Now, we have option maturity $T_o$, discount factor $DF_{T_o}$ (correspoding to discount rate), future expory $T_f$, future value $F_{T_f}$, option price ($C_i$ cand $P_i$), and strike $K_i$. Therefore, we can imply volatility $\sigma_{T_o}(K_i)$ using a standard Black-Scholes formula.

## BTC/USD Risk-Neutral Probability
Risk Neutral Probability density function is implied from Breeden-Litzenberger formula:

$\phi(k) = \frac{\partial^2}{\partial k^2}V(S,T,k)$

where $V(S,T,k)$ is undiscounted call/put price (both option types should return the same result if non-arbitrage condition holds).  


Because the option price is rounded to USD 5, this disturbes the second derivative and gives noisy density.
To address the issue, the orginal undiscounted option price $\hat{V}(S,T,k)$ is smoothed by minimizing a loss function:  

$L(\{V(k)\};\{\hat{V}(k)\}) = \int dk\frac{1}{2D^2}[\frac{\partial^2}{\partial k^2}V(k)]^2 + \int dk\frac{1}{2s^2}(V(k)-\hat{V}(k))^2$
  
where $s$ is USD5 and $D$ is max value of slope of density function of log-normal density assuming volatility implied from ATM price $\hat{V}(k=F)$.

The minimization problem is solved after the loss function is discretized along strike.  

The second derivative for the density computation uses discretization of the original strike grid in data because it is dense.  So, interpolation is not used.  For extrapolation, Pareto tails are calibrated to the both sides.


## BTC/USD Moment Analysis
The goal is to predict probability of spot price at future time.  

To do this, we try to predict moments of spot price under physical measure from moments under risk-neutral measure using probability in the last section, similarly to [Forecasting swap rate volatility with information from swaptions, A Liu and J Xie, 2023](https://www.bis.org/publ/work1068.pdf).  

Lasso regression is used to link physical moments with risk-neutral moments. However, due to a lack of data points. There is no meaningful result at this moment.  
