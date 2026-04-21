-- Migration v3.1: Add Day High and Day Low to Backtest Trades
-- Purpose: Enable high/low visualization and data points in backtest results.
-- Run this in Supabase SQL Editor.

ALTER TABLE backtest_trades ADD COLUMN day_high NUMERIC(12,2);
ALTER TABLE backtest_trades ADD COLUMN day_low NUMERIC(12,2);

COMMENT ON COLUMN backtest_trades.day_high IS 'The high price for the stock on this trade date.';
COMMENT ON COLUMN backtest_trades.day_low IS 'The low price for the stock on this trade date.';
