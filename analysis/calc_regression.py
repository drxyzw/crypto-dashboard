from datetime import datetime as dt
import pandas as pd
from sklearn.linear_model import LassoCV 

ANALYZED_DIR = "./data_analyzed"
MOMENT_FILE = ANALYZED_DIR + "/moment.xlsx"
REGRESSION_FILE = ANALYZED_DIR + "/regression.xlsx"
VS_PREDICTION_FILE = ANALYZED_DIR + "/vsPrediction.xlsx"

if __name__ == "__main__":
    df_moment = pd.read_excel(MOMENT_FILE)
    df = df_moment.dropna()
    df_predict = df.copy()
    x_columns = ["M1_RN", "CM2_RN", "CMN3_RN", "CMN4_RN"]
    y_columns = ["M1_PH", "CM2_PH", "CMN3_PH", "CMN4_PH"]

    X = df[x_columns]
    dfs_result = []
    for y_column in y_columns:
        y = df[y_column]
        model = LassoCV()
        reg_result = model.fit(X, y)
        betas = list(reg_result.coef_)
        intercept = reg_result.intercept_
        r2 = reg_result.score(X, y)
        cols = ["Target", ] + ["Beta_" + col for col in y_columns] + ["intercept", "R2"]
        values = [y_column] + betas + [intercept, r2]
        values_vec = [[v] for v in values]
        dict_result = dict(zip(cols, values_vec))
        df_result_i = pd.DataFrame(dict_result)
        dfs_result.append(df_result_i)
        y_predict = reg_result.predict(X)
        df_predict[y_column + "_pred"] = y_predict

    df_result = pd.concat(dfs_result)
    df_result.to_excel(REGRESSION_FILE, index=False)
    df_predict.to_excel(VS_PREDICTION_FILE, index=False)

