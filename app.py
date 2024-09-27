import numpy as np
import yfinance as yf
from flask import Flask, render_template, request
import pandas as pd
app = Flask(__name__)


def get_financial_data(ticker):
    stock = yf.Ticker(ticker)
    financials = stock.financials
    balance_sheet = stock.balance_sheet
    cash_flow = stock.cashflow
    return financials, balance_sheet, cash_flow


def calculate_metrics(financials, balance_sheet, cash_flow, growth_rate, discount_rate, years):
    # Revenue growth
    revenue_growth = financials.loc['Total Revenue'].pct_change().mean()

    # Operating margin
    operating_margin = financials.loc['Operating Income'] / financials.loc['Total Revenue']

    # Check for working capital data
    total_current_assets = balance_sheet.loc['Total Assets'] if 'Total Assets' in balance_sheet.index else np.nan
    total_current_liabilities = balance_sheet.loc[
        'Total Liabilities Net Minority Interest'] if 'Total Liabilities Net Minority Interest' in balance_sheet.index else np.nan

    if total_current_assets is not np.nan and total_current_liabilities is not np.nan:
        working_capital = total_current_assets - total_current_liabilities
    else:
        working_capital = np.nan  # Set to NaN if not found

    # Capital Expenditure
    capex = cash_flow.loc['Capital Expenditure'].mean() if 'Capital Expenditure' in cash_flow.index else np.nan

    # Free Cash Flow (Simplified)
    net_income = cash_flow.loc['Net Income'] if 'Net Income' in cash_flow.index else np.nan
    depreciation = cash_flow.loc['Depreciation'] if 'Depreciation' in cash_flow.index else np.nan
    changes_in_working_capital = cash_flow.loc[
        'Change In Working Capital'] if 'Change In Working Capital' in cash_flow.index else np.nan
    if pd.notna(net_income) and pd.notna(depreciation) and pd.notna(changes_in_working_capital) and pd.notna(capex):
        fcf = net_income + depreciation - changes_in_working_capital - capex
    else:
        fcf = np.nan  # Set to NaN if not enough data

    # FCF Projections
    fcf_projections = [fcf * (1 + growth_rate) ** i for i in range(1, years + 1)] if pd.notna(fcf) else [np.nan] * years

    # Terminal Value (Gordon Growth Model)
    terminal_value = fcf_projections[-1] * (1 + growth_rate) / (discount_rate - growth_rate) if pd.notna(
        fcf_projections[-1]) else np.nan

    # Discount Factors
    discount_factors = [1 / (1 + discount_rate) ** i for i in range(1, years + 1)]

    # Present Value of FCF
    present_value_fcf = sum(fcf_proj * df for fcf_proj, df in zip(fcf_projections, discount_factors)) if pd.notna(
        fcf) else np.nan

    # Present Value of Terminal Value
    present_value_terminal = terminal_value / (1 + discount_rate) ** years if pd.notna(terminal_value) else np.nan

    # Enterprise Value
    enterprise_value = present_value_fcf + present_value_terminal if pd.notna(present_value_fcf) and pd.notna(
        present_value_terminal) else np.nan

    return {
        'revenue_growth': revenue_growth,
        'operating_margin': operating_margin.mean(),
        'working_capital': working_capital.mean() if isinstance(working_capital, (int, float)) else np.nan,
        'capex': capex,
        'fcf_projections': fcf_projections,
        'discount_factors': discount_factors,
        'present_value_fcf': present_value_fcf,
        'present_value_terminal': present_value_terminal,
        'enterprise_value': enterprise_value
    }


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        ticker = request.form['ticker']
        growth_rate = float(request.form['growth_rate'])
        discount_rate = float(request.form['discount_rate'])
        years = int(request.form['years'])

        # Get financial data and calculate metrics
        financials, balance_sheet, cash_flow = get_financial_data(ticker)
        metrics = calculate_metrics(financials, balance_sheet, cash_flow, growth_rate, discount_rate, years)

        return render_template('results.html', metrics=metrics, ticker=ticker)

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
