from sklearn.linear_model import LassoCV 
import numpy as np
class LassoCVStndardize():
    lassocv_internal = None
    X_mean = np.array([])
    X_std = np.array([])
    coef_ = None
    intercept_ = None

    def __init__(self):
        self.lassocv_internal = LassoCV()
    
    def fit(self, X, y):
        self.X_mean = X.mean(axis=0)
        self.X_std = X.std(axis=0)
        X_standardize = (X -self.X_mean)  / self.X_std
        self.lassocv_internal.fit(X_standardize, y)

        coef_internal = self.lassocv_internal.coef_
        intercept_internal = self.lassocv_internal.intercept_
        
        self.coef_ = coef_internal / self.X_std
        self.intercept_ = intercept_internal - np.dot(self.coef_, self.X_mean)
        return self
    
    def score(self, X, y):
        X_standardize = (X -self.X_mean)  / self.X_std
        return self.lassocv_internal.score(X_standardize, y)

    def predict(self, X):
        X_standardize = (X -self.X_mean)  / self.X_std
        return self.lassocv_internal.predict(X_standardize)




        