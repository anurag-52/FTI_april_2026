-- ============================================================
-- COURTNEY SMITH CHANNEL BREAKOUT TRADING PLATFORM
-- Database Schema v3.0 — Final — Approved for Production
-- Compatible with: Supabase (PostgreSQL)
-- Instructions: Paste entire file into Supabase SQL Editor → Run
-- ============================================================

-- ============================================================
-- TABLE 1: users
-- All accounts — super admin (role='admin') and traders (role='trader')
-- No self-registration. Super Admin creates all trader accounts.
-- ============================================================
CREATE TABLE users (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name               TEXT NOT NULL,
  email                   TEXT UNIQUE NOT NULL,
  mobile                  TEXT,
  role                    TEXT NOT NULL DEFAULT 'trader'
                            CHECK (role IN ('admin', 'trader')),
  status                  TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'paused', 'suspended')),
  -- Capital
  starting_capital        NUMERIC(15,2) NOT NULL DEFAULT 0,
  available_capital       NUMERIC(15,2) NOT NULL DEFAULT 0,
  -- Risk setting (Courtney Smith Fixed Fractional — default 1%)
  risk_percent            NUMERIC(5,2) NOT NULL DEFAULT 1.00
                            CHECK (risk_percent >= 0.5 AND risk_percent <= 5.0),
  -- Notifications
  notify_email            BOOLEAN NOT NULL DEFAULT TRUE,
  notify_whatsapp         BOOLEAN NOT NULL DEFAULT FALSE,
  -- Confirmation state
  confirmation_pending    BOOLEAN NOT NULL DEFAULT FALSE,
  last_confirmed_at       TIMESTAMPTZ,
  -- Inactivity tracking (counts market open days only)
  inactivity_days         INTEGER NOT NULL DEFAULT 0,
  warned_day5             BOOLEAN NOT NULL DEFAULT FALSE,
  warned_day12            BOOLEAN NOT NULL DEFAULT FALSE,
  -- First login enforcement
  first_login_complete    BOOLEAN NOT NULL DEFAULT FALSE,
  password_changed        BOOLEAN NOT NULL DEFAULT FALSE,
  capital_entered         BOOLEAN NOT NULL DEFAULT FALSE,
  -- Account management
  created_by              UUID REFERENCES users(id),
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE 2: stocks
-- Central registry of all unique stocks across all watchlists.
-- Data fetched once, shared across all traders.
-- ============================================================
CREATE TABLE stocks (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker_nse        TEXT UNIQUE,           -- e.g. RELIANCE (yfinance: RELIANCE.NS)
  ticker_bse        TEXT UNIQUE,           -- e.g. 500325
  company_name      TEXT NOT NULL,
  exchange          TEXT NOT NULL CHECK (exchange IN ('NSE', 'BSE')),
  sector            TEXT,
  -- Data fetch status
  history_fetched   BOOLEAN NOT NULL DEFAULT FALSE,
  history_from_date DATE,
  history_to_date   DATE,
  data_fetched_at   TIMESTAMPTZ,
  -- Background job status for new stocks
  compute_status    TEXT NOT NULL DEFAULT 'pending'
                      CHECK (compute_status IN ('pending','running','complete','failed')),
  compute_progress  INTEGER DEFAULT 0,     -- 0-100 percent
  -- Suspension/delisting detection
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  is_suspended      BOOLEAN NOT NULL DEFAULT FALSE,
  suspended_at      TIMESTAMPTZ,
  missing_data_days INTEGER NOT NULL DEFAULT 0,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE 3: stock_prices
-- Central EOD price data + ALL pre-computed indicators and
-- signal flags. Computed ONCE per stock per day.
-- Never recalculated per trader or per backtest run.
-- ============================================================
CREATE TABLE stock_prices (
  id                    BIGSERIAL PRIMARY KEY,
  stock_id              UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
  price_date            DATE NOT NULL,
  -- Raw OHLCV
  open                  NUMERIC(12,2),
  high                  NUMERIC(12,2) NOT NULL,
  low                   NUMERIC(12,2) NOT NULL,
  close                 NUMERIC(12,2) NOT NULL,
  volume                BIGINT,
  -- Channel indicators
  ch55_high             NUMERIC(12,2),    -- 55-day channel high
  ch55_low              NUMERIC(12,2),    -- 55-day channel low
  ch20_high             NUMERIC(12,2),    -- 20-day channel high
  ch20_low              NUMERIC(12,2),    -- 20-day channel low = trailing stop
  -- ADX
  adx_20                NUMERIC(8,4),     -- ADX(20) value
  adx_rising            BOOLEAN,          -- TRUE if today ADX > yesterday ADX
  -- Channel flat/declining count
  ch55_high_flat_days   INTEGER,          -- consecutive days 55-high flat/declining
  ch55_low_flat_days    INTEGER,          -- consecutive days 55-low flat/rising
  -- PRE-COMPUTED SIGNAL FLAGS (core of the system)
  buy_signal            BOOLEAN NOT NULL DEFAULT FALSE,  -- all 3 buy conditions met
  exit_rejection        BOOLEAN NOT NULL DEFAULT FALSE,  -- rejection rule triggered
  exit_trailing_stop    BOOLEAN NOT NULL DEFAULT FALSE,  -- close < 20-day low
  exit_adx              BOOLEAN NOT NULL DEFAULT FALSE,  -- ADX turned down from 40+
  any_exit_signal       BOOLEAN NOT NULL DEFAULT FALSE,  -- any of 3 exit conditions
  -- Indian market specifics
  hit_upper_circuit     BOOLEAN NOT NULL DEFAULT FALSE,
  hit_lower_circuit     BOOLEAN NOT NULL DEFAULT FALSE,
  circuit_limit_pct     NUMERIC(5,2),     -- 5, 10, or 20 percent
  -- Gap risk (post-holiday)
  is_post_holiday       BOOLEAN NOT NULL DEFAULT FALSE,
  gap_down_pct          NUMERIC(8,4),     -- % gap down from pre-holiday close
  gap_risk_warning      BOOLEAN NOT NULL DEFAULT FALSE,  -- gap > 2%
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (stock_id, price_date)
);

CREATE INDEX idx_stock_prices_stock_date
  ON stock_prices(stock_id, price_date DESC);
CREATE INDEX idx_stock_prices_buy_signal
  ON stock_prices(price_date, buy_signal) WHERE buy_signal = TRUE;
CREATE INDEX idx_stock_prices_exit_signal
  ON stock_prices(price_date, any_exit_signal) WHERE any_exit_signal = TRUE;

-- ============================================================
-- TABLE 4: watchlists
-- Each trader's personal list of up to 30 active stocks.
-- Stocks can be deactivated (not deleted) to make room.
-- Cannot deactivate if open position exists.
-- ============================================================
CREATE TABLE watchlists (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  stock_id      UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  added_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deactivated_at TIMESTAMPTZ,
  UNIQUE (user_id, stock_id)
);

CREATE INDEX idx_watchlists_user_active
  ON watchlists(user_id, is_active) WHERE is_active = TRUE;

-- ============================================================
-- TABLE 5: signals
-- Daily buy/exit signals per trader per stock.
-- Generated by scan engine reading pre-computed stock_prices flags.
-- ============================================================
CREATE TABLE signals (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  stock_id              UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
  signal_date           DATE NOT NULL,
  signal_type           TEXT NOT NULL
                          CHECK (signal_type IN ('BUY','EXIT_REJECTION',
                                                 'EXIT_TRAILING','EXIT_ADX')),
  -- Signal values at time of generation (from stock_prices)
  trigger_price         NUMERIC(12,2) NOT NULL,
  ch55_high_at_signal   NUMERIC(12,2),
  ch20_low_at_signal    NUMERIC(12,2),     -- trailing stop level
  adx_at_signal         NUMERIC(8,4),
  flat_days             INTEGER,
  -- Suggested qty (Courtney Smith Fixed Fractional formula)
  suggested_qty         INTEGER,
  suggested_cost        NUMERIC(15,2),
  -- Warnings
  circuit_warning       BOOLEAN NOT NULL DEFAULT FALSE,
  circuit_type          TEXT CHECK (circuit_type IN ('UPPER','LOWER')),
  gap_risk_warning      BOOLEAN NOT NULL DEFAULT FALSE,
  gap_down_pct          NUMERIC(8,4),
  -- Trader confirmation (NULL=pending, TRUE=actioned, FALSE=skipped)
  confirmed             BOOLEAN DEFAULT NULL,
  confirmed_at          TIMESTAMPTZ,
  confirmed_qty         INTEGER,
  confirmed_price       NUMERIC(12,2),
  -- Notification
  notification_sent     BOOLEAN NOT NULL DEFAULT FALSE,
  notification_sent_at  TIMESTAMPTZ,
  -- Permanent notification token (no expiry)
  notification_token    TEXT UNIQUE,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, stock_id, signal_date, signal_type)
);

CREATE INDEX idx_signals_user_date
  ON signals(user_id, signal_date DESC);
CREATE INDEX idx_signals_pending
  ON signals(user_id, confirmed) WHERE confirmed IS NULL;
CREATE INDEX idx_signals_token
  ON signals(notification_token);

-- ============================================================
-- TABLE 6: notification_sessions
-- Tracks the permanent link token per trader per signal date.
-- One session per trader per day. Link stays active until
-- SUBMIT is clicked or account is paused/suspended.
-- ============================================================
CREATE TABLE notification_sessions (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  signal_date       DATE NOT NULL,
  session_token     TEXT UNIQUE NOT NULL,
  has_signals       BOOLEAN NOT NULL DEFAULT TRUE,  -- FALSE = no-signal day
  total_rows        INTEGER NOT NULL DEFAULT 0,     -- total buy+exit rows
  actioned_rows     INTEGER NOT NULL DEFAULT 0,     -- rows trader has actioned
  submitted         BOOLEAN NOT NULL DEFAULT FALSE,  -- SUBMIT button clicked
  submitted_at      TIMESTAMPTZ,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, signal_date)
);

-- ============================================================
-- TABLE 7: positions
-- Open and closed stock positions per trader.
-- Created when trader confirms BUY. Closed on confirmed EXIT.
-- Multiple open positions in same stock allowed.
-- On exit signal: ALL positions in that stock exit simultaneously.
-- ============================================================
CREATE TABLE positions (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  stock_id          UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
  signal_id         UUID REFERENCES signals(id),
  -- Entry
  entry_date        DATE NOT NULL,
  entry_price       NUMERIC(12,2) NOT NULL,
  quantity          INTEGER NOT NULL,
  total_invested    NUMERIC(15,2) NOT NULL,
  -- Position source
  source            TEXT NOT NULL DEFAULT 'SIGNAL'
                      CHECK (source IN ('SIGNAL','MANUAL')),
  -- Status
  status            TEXT NOT NULL DEFAULT 'open'
                      CHECK (status IN ('open','closed')),
  -- Exit
  exit_date         DATE,
  exit_price        NUMERIC(12,2),
  exit_reason       TEXT CHECK (exit_reason IN (
                      'REJECTION_RULE','TRAILING_STOP',
                      'ADX_EXIT','MANUAL')),
  exit_signal_id    UUID REFERENCES signals(id),
  total_exit_value  NUMERIC(15,2),
  pnl_amount        NUMERIC(15,2),
  pnl_percent       NUMERIC(8,4),
  days_held         INTEGER,
  -- Rejection rule tracking
  days_since_entry  INTEGER NOT NULL DEFAULT 0,
  -- Flags
  gap_risk_on_exit  BOOLEAN NOT NULL DEFAULT FALSE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_positions_user_open
  ON positions(user_id, status) WHERE status = 'open';
CREATE INDEX idx_positions_user_stock
  ON positions(user_id, stock_id, status);

-- ============================================================
-- TABLE 8: capital_log
-- Full audit trail of every capital change per trader.
-- Every deposit, withdrawal, buy, sell, and admin adjustment
-- logged with amount, balance, date, time, and who made change.
-- ============================================================
CREATE TABLE capital_log (
  id              BIGSERIAL PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  change_type     TEXT NOT NULL CHECK (change_type IN (
                    'DEPOSIT','WITHDRAWAL','BUY','SELL',
                    'PARTIAL_SELL','ADMIN_ADJUST')),
  amount          NUMERIC(15,2) NOT NULL,   -- positive=added, negative=deducted
  balance_after   NUMERIC(15,2) NOT NULL,
  notes           TEXT,
  position_id     UUID REFERENCES positions(id),
  signal_id       UUID REFERENCES signals(id),
  changed_by      UUID REFERENCES users(id), -- trader or admin
  source          TEXT NOT NULL DEFAULT 'SIGNAL'
                    CHECK (source IN ('SIGNAL','MANUAL','ADMIN')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_capital_log_user
  ON capital_log(user_id, created_at DESC);

-- ============================================================
-- TABLE 9: backtest_runs
-- Each backtest run by a trader (up to 7 stocks simultaneously).
-- Shared capital pool across all stocks in the run.
-- ============================================================
CREATE TABLE backtest_runs (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  -- Up to 7 stock IDs stored as array
  stock_ids             UUID[] NOT NULL,
  stock_names           TEXT[],
  from_date             DATE NOT NULL,
  to_date               DATE NOT NULL,
  starting_capital      NUMERIC(15,2) NOT NULL,
  position_size_type    TEXT NOT NULL
                          CHECK (position_size_type IN ('FIXED_AMOUNT','PERCENT_CAPITAL')),
  position_size_value   NUMERIC(15,2) NOT NULL,
  risk_percent          NUMERIC(5,2) NOT NULL DEFAULT 1.00,
  -- Combined portfolio results
  total_trades          INTEGER,
  winning_trades        INTEGER,
  losing_trades         INTEGER,
  win_rate_percent      NUMERIC(8,4),
  avg_profit_percent    NUMERIC(8,4),
  avg_loss_percent      NUMERIC(8,4),
  max_drawdown_percent  NUMERIC(8,4),
  final_capital         NUMERIC(15,2),
  total_return_percent  NUMERIC(8,4),
  -- Equity curve: [{date, capital_value}, ...]
  equity_curve          JSONB,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE 10: backtest_trades
-- Individual trade log per backtest run.
-- Day-by-day simulation data stored here.
-- ============================================================
CREATE TABLE backtest_trades (
  id              BIGSERIAL PRIMARY KEY,
  backtest_id     UUID NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
  stock_id        UUID NOT NULL REFERENCES stocks(id),
  trade_date      DATE NOT NULL,
  -- All indicator values for this day (pre-computed from stock_prices)
  close_price     NUMERIC(12,2),
  ch55_high       NUMERIC(12,2),
  ch55_low        NUMERIC(12,2),
  ch20_high       NUMERIC(12,2),
  ch20_low        NUMERIC(12,2),
  adx_value       NUMERIC(8,4),
  adx_rising      BOOLEAN,
  flat_days       INTEGER,
  -- Signal flags for this day
  buy_signal      BOOLEAN,
  exit_rejection  BOOLEAN,
  exit_trailing   BOOLEAN,
  exit_adx        BOOLEAN,
  -- Action taken
  action          TEXT CHECK (action IN ('BUY','SELL','HOLD','SKIPPED_CAPITAL',NULL)),
  entry_price     NUMERIC(12,2),
  exit_price      NUMERIC(12,2),
  quantity        INTEGER,
  exit_reason     TEXT,
  pnl_amount      NUMERIC(15,2),
  pnl_percent     NUMERIC(8,4),
  days_held       INTEGER,
  capital_after   NUMERIC(15,2)
);

CREATE INDEX idx_backtest_trades_run
  ON backtest_trades(backtest_id, trade_date);

-- ============================================================
-- TABLE 11: market_holidays
-- NSE official holiday calendar. Fetched annually + weekly refresh.
-- Super Admin can manually add/edit/remove holidays.
-- ============================================================
CREATE TABLE market_holidays (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  holiday_date    DATE UNIQUE NOT NULL,
  holiday_name    TEXT NOT NULL,
  exchange        TEXT NOT NULL DEFAULT 'NSE' CHECK (exchange IN ('NSE','BSE','BOTH')),
  source          TEXT NOT NULL DEFAULT 'AUTO'
                    CHECK (source IN ('AUTO','ADMIN_MANUAL')),
  added_by        UUID REFERENCES users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_market_holidays_date
  ON market_holidays(holiday_date);

-- ============================================================
-- TABLE 12: scan_log
-- Daily scan engine run history. Every attempt logged.
-- Visible on both Super Admin and Trader dashboards.
-- ============================================================
CREATE TABLE scan_log (
  id                  BIGSERIAL PRIMARY KEY,
  scan_date           DATE NOT NULL,
  started_at          TIMESTAMPTZ NOT NULL,
  completed_at        TIMESTAMPTZ,
  status              TEXT NOT NULL
                        CHECK (status IN ('running','completed','failed',
                                          'skipped_holiday','aborted_holiday')),
  data_source         TEXT CHECK (data_source IN (
                        'yfinance','nse_bhavcopy','bse_bhavcopy')),
  retry_attempt       INTEGER NOT NULL DEFAULT 1,   -- which attempt (1-12)
  stocks_scanned      INTEGER,
  signals_generated   INTEGER,
  errors              TEXT,
  triggered_by        TEXT NOT NULL DEFAULT 'AUTO'
                        CHECK (triggered_by IN ('AUTO','ADMIN','TRADER')),
  triggered_by_user   UUID REFERENCES users(id)
);

-- ============================================================
-- TABLE 13: notification_log
-- Full audit trail of every WhatsApp and Email sent.
-- ============================================================
CREATE TABLE notification_log (
  id                  BIGSERIAL PRIMARY KEY,
  user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  channel             TEXT NOT NULL CHECK (channel IN ('EMAIL','WHATSAPP')),
  notification_type   TEXT NOT NULL CHECK (notification_type IN (
                        'DAILY_SIGNAL','NO_SIGNAL_DAY','EXIT_ALERT',
                        'REMINDER','INACTIVITY_DAY5','INACTIVITY_DAY12',
                        'AUTO_PAUSED','AUTO_SUSPENDED','MARKET_HOLIDAY',
                        'HOLIDAY_CALENDAR_CHANGE','SCAN_FAILURE',
                        'CIRCUIT_WARNING','GAP_RISK_WARNING',
                        'STOCK_SUSPENDED','SYSTEM')),
  subject             TEXT,
  body_preview        TEXT,                         -- first 300 chars
  status              TEXT NOT NULL CHECK (status IN ('sent','failed','pending')),
  provider_ref        TEXT,                         -- MSG91 or Brevo message ID
  sent_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notification_log_user
  ON notification_log(user_id, sent_at DESC);

-- ============================================================
-- TABLE 14: data_source_log
-- Tracks every data fetch attempt — source, status, retry count.
-- Visible on Super Admin and Trader dashboards.
-- ============================================================
CREATE TABLE data_source_log (
  id              BIGSERIAL PRIMARY KEY,
  fetch_date      DATE NOT NULL,
  stock_id        UUID REFERENCES stocks(id),       -- NULL = bulk fetch
  source          TEXT NOT NULL CHECK (source IN (
                    'yfinance','nse_bhavcopy','bse_bhavcopy')),
  attempt_number  INTEGER NOT NULL DEFAULT 1,       -- 1-12
  status          TEXT NOT NULL CHECK (status IN ('success','failed','retrying')),
  error_message   TEXT,
  triggered_by    TEXT NOT NULL DEFAULT 'AUTO'
                    CHECK (triggered_by IN ('AUTO','ADMIN','TRADER')),
  triggered_by_user UUID REFERENCES users(id),
  attempted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_data_source_log_date
  ON data_source_log(fetch_date DESC);

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- Traders see only their own data.
-- Backend uses service_role key (bypasses RLS) for all writes.
-- ============================================================
ALTER TABLE users                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlists            ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals               ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions             ENABLE ROW LEVEL SECURITY;
ALTER TABLE capital_log           ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtest_runs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtest_trades       ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_log      ENABLE ROW LEVEL SECURITY;

-- Traders read/write own rows only
CREATE POLICY "own_watchlists" ON watchlists
  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own_signals" ON signals
  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own_sessions" ON notification_sessions
  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own_positions" ON positions
  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own_capital_log" ON capital_log
  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own_backtests" ON backtest_runs
  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own_notifications" ON notification_log
  FOR ALL USING (auth.uid() = user_id);

-- Stocks, stock_prices, market_holidays, scan_log, data_source_log
-- readable by all authenticated users
ALTER TABLE stocks            ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_prices      ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_holidays   ENABLE ROW LEVEL SECURITY;
ALTER TABLE scan_log          ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_source_log   ENABLE ROW LEVEL SECURITY;

CREATE POLICY "auth_read_stocks" ON stocks
  FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "auth_read_prices" ON stock_prices
  FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "auth_read_holidays" ON market_holidays
  FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "auth_read_scan_log" ON scan_log
  FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "auth_read_data_log" ON data_source_log
  FOR SELECT USING (auth.role() = 'authenticated');

-- ============================================================
-- SEED: Super Admin Account
-- Run ONCE after setup. Then create Supabase Auth user manually
-- at supabase.com → Authentication → Users → Invite User
-- Email: aaanurag@yahoo.com  Password: Anurag75*
-- ============================================================
INSERT INTO users (
  full_name, email, mobile, role, status,
  starting_capital, available_capital,
  notify_email, notify_whatsapp,
  first_login_complete, password_changed, capital_entered
) VALUES (
  'Anurag', 'aaanurag@yahoo.com', '9303121500', 'admin', 'active',
  0, 0,
  TRUE, TRUE,
  TRUE, TRUE, TRUE
);
