
CREATE DATABASE IF NOT EXISTS StockPortfolioDB;
USE StockPortfolioDB;

-- 1. STOCKS TABLE
CREATE TABLE IF NOT EXISTS popular_stocks (
    stock_id INT AUTO_INCREMENT PRIMARY KEY,
    stock_name VARCHAR(100) NOT NULL,
    stock_symbol VARCHAR(30) NOT NULL UNIQUE,
    sector VARCHAR(50),
    current_price DECIMAL(12,2),
    price_date DATETIME,
    CHECK (current_price IS NULL OR current_price >= 0)
) ENGINE=InnoDB;

-- 2. USER PORTFOLIO TABLE
CREATE TABLE IF NOT EXISTS user_portfolio (
    portfolio_id INT AUTO_INCREMENT PRIMARY KEY,
    user_name VARCHAR(100) NOT NULL,
    stock_id INT NOT NULL,
    buying_price DECIMAL(12,2) NOT NULL CHECK (buying_price > 0),
    quantity INT NOT NULL CHECK (quantity > 0),
    buy_date DATE NOT NULL,
    notes VARCHAR(100),
    FOREIGN KEY (stock_id) REFERENCES popular_stocks(stock_id)
) ENGINE=InnoDB;

-- 3. PRICE AUDIT TABLE
CREATE TABLE IF NOT EXISTS price_audit (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    stock_id INT NOT NULL,
    old_price DECIMAL(12,2),
    new_price DECIMAL(12,2),
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES popular_stocks(stock_id)
) ENGINE=InnoDB;

-- 4. STOCK SUMMARY TABLE
CREATE TABLE IF NOT EXISTS stock_summary (
    stock_id INT PRIMARY KEY,
    total_quantity INT DEFAULT 0,
    total_invested DECIMAL(14,2) DEFAULT 0,
    FOREIGN KEY (stock_id) REFERENCES popular_stocks(stock_id)
) ENGINE=InnoDB;

-- 5. ADD NOTES COLUMN IF MISSING
SET @notes_exists = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = 'StockPortfolioDB'
      AND table_name = 'user_portfolio'
      AND column_name = 'notes'
);

SET @notes_sql = IF(
    @notes_exists = 0,
    'ALTER TABLE user_portfolio ADD COLUMN notes VARCHAR(100)',
    'SELECT ''notes column already exists'' AS message'
);

PREPARE notes_stmt FROM @notes_sql;
EXECUTE notes_stmt;
DEALLOCATE PREPARE notes_stmt;

-- 6. INSERT FIVE STOCKS; NO DEMO USERS
INSERT INTO popular_stocks
    (stock_name, stock_symbol, sector)
VALUES
    ('Reliance Industries', 'RELIANCE.NS', 'Energy'),
    ('TCS', 'TCS.NS', 'IT'),
    ('HDFC Bank', 'HDFCBANK.NS', 'Banking'),
    ('ICICI Bank', 'ICICIBANK.NS', 'Banking'),
    ('Infosys', 'INFY.NS', 'IT')
ON DUPLICATE KEY UPDATE
    stock_name = VALUES(stock_name),
    sector = VALUES(sector);

-- 7. PORTFOLIO JOIN AND PROFIT/LOSS
SELECT
    p.user_name,
    s.stock_name,
    p.buying_price,
    s.current_price,
    p.quantity,
    p.buying_price * p.quantity AS invested,
    s.current_price * p.quantity AS current_value,
    (s.current_price - p.buying_price) * p.quantity AS profit_loss
FROM user_portfolio p
JOIN popular_stocks s ON p.stock_id = s.stock_id;

-- 8. AGGREGATE FUNCTIONS
SELECT
    COALESCE(SUM(p.buying_price * p.quantity), 0) AS total_invested,
    COALESCE(SUM(s.current_price * p.quantity), 0) AS current_value,
    COALESCE(SUM((s.current_price - p.buying_price) * p.quantity), 0) AS total_pnl
FROM user_portfolio p
JOIN popular_stocks s ON p.stock_id = s.stock_id;

-- 9. FILTER AND SORT
SELECT stock_name, stock_symbol, current_price
FROM popular_stocks
WHERE sector = 'Banking'
ORDER BY stock_name;

-- 10. GROUP BY AND HAVING
SELECT sector, COUNT(*) AS total_stocks
FROM popular_stocks
GROUP BY sector
HAVING COUNT(*) > 1;

-- 11. SUBQUERY
SELECT stock_name, current_price
FROM popular_stocks
WHERE current_price > (
    SELECT AVG(current_price)
    FROM popular_stocks
    WHERE current_price IS NOT NULL
);

-- 12. VIEW
CREATE OR REPLACE VIEW v_user_portfolio AS
SELECT
    p.portfolio_id,
    p.user_name,
    s.stock_name,
    s.stock_symbol,
    p.buying_price,
    s.current_price,
    p.quantity,
    p.buying_price * p.quantity AS invested,
    s.current_price * p.quantity AS current_value,
    (s.current_price - p.buying_price) * p.quantity AS profit_loss
FROM user_portfolio p
JOIN popular_stocks s ON p.stock_id = s.stock_id;

-- 13. INDEXES: CREATE ONLY IF MISSING
SET @idx_sql = IF(
    (SELECT COUNT(*) FROM information_schema.statistics
     WHERE table_schema = 'StockPortfolioDB'
       AND table_name = 'popular_stocks'
       AND index_name = 'idx_stock_sector') = 0,
    'CREATE INDEX idx_stock_sector ON popular_stocks(sector)',
    'SELECT ''Sector index exists'' AS message'
);
PREPARE idx_stmt FROM @idx_sql;
EXECUTE idx_stmt;
DEALLOCATE PREPARE idx_stmt;

SET @idx_sql = IF(
    (SELECT COUNT(*) FROM information_schema.statistics
     WHERE table_schema = 'StockPortfolioDB'
       AND table_name = 'user_portfolio'
       AND index_name = 'idx_user_name') = 0,
    'CREATE INDEX idx_user_name ON user_portfolio(user_name)',
    'SELECT ''User index exists'' AS message'
);
PREPARE idx_stmt FROM @idx_sql;
EXECUTE idx_stmt;
DEALLOCATE PREPARE idx_stmt;

-- 14. PROFIT/LOSS FUNCTION
DROP FUNCTION IF EXISTS fn_profit_loss;
DELIMITER //

CREATE FUNCTION fn_profit_loss(
    buy_price DECIMAL(12,2),
    market_price DECIMAL(12,2),
    shares INT
)
RETURNS DECIMAL(14,2)
DETERMINISTIC
NO SQL
BEGIN
    RETURN (market_price - buy_price) * shares;
END //

-- 15. PORTFOLIO PROCEDURE
DROP PROCEDURE IF EXISTS sp_show_portfolio //

CREATE PROCEDURE sp_show_portfolio(IN p_user VARCHAR(100))
BEGIN
    SELECT *
    FROM v_user_portfolio
    WHERE user_name = p_user;
END //

-- 16. PRICE AUDIT TRIGGER
DROP TRIGGER IF EXISTS trg_price_update //

CREATE TRIGGER trg_price_update
AFTER UPDATE ON popular_stocks
FOR EACH ROW
BEGIN
    IF NOT (OLD.current_price <=> NEW.current_price) THEN
        INSERT INTO price_audit (stock_id, old_price, new_price)
        VALUES (NEW.stock_id, OLD.current_price, NEW.current_price);
    END IF;
END //

-- 17. SUMMARY CURSOR PROCEDURE
DROP PROCEDURE IF EXISTS sp_build_summary //

CREATE PROCEDURE sp_build_summary()
BEGIN
    DECLARE finished INT DEFAULT 0;
    DECLARE sid INT;
    DECLARE qty INT;
    DECLARE invested_amount DECIMAL(14,2);

    DECLARE stock_cursor CURSOR FOR
        SELECT stock_id, SUM(quantity), SUM(buying_price * quantity)
        FROM user_portfolio
        GROUP BY stock_id;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET finished = 1;

    DELETE FROM stock_summary;
    OPEN stock_cursor;

    read_loop: LOOP
        FETCH stock_cursor INTO sid, qty, invested_amount;
        IF finished = 1 THEN
            LEAVE read_loop;
        END IF;

        INSERT INTO stock_summary
            (stock_id, total_quantity, total_invested)
        VALUES (sid, qty, invested_amount);
    END LOOP;

    CLOSE stock_cursor;
END //

DELIMITER ;

-- 18. TEST FUNCTION
SELECT fn_profit_loss(1200, 1250, 10) AS profit_loss;

-- 19. TEST PROCEDURE WITH NO DEMO USERS
CALL sp_show_portfolio('Your User Name');

-- 20. REFRESH SUMMARY
CALL sp_build_summary();

-- 21. TRANSACTION TEST; NO ROW IS MODIFIED
START TRANSACTION;
UPDATE user_portfolio
SET quantity = quantity + 1
WHERE portfolio_id = -1;
ROLLBACK;

-- 22. FINAL RESULTS
SELECT COUNT(*) AS total_stocks FROM popular_stocks;
SELECT COUNT(DISTINCT user_name) AS total_users FROM user_portfolio;
SELECT DISTINCT user_name FROM user_portfolio;
SELECT stock_name, stock_symbol FROM popular_stocks ORDER BY stock_id;
SELECT * FROM user_portfolio;
SELECT * FROM v_user_portfolio;
SELECT * FROM price_audit ORDER BY audit_id;
SELECT * FROM stock_summary ORDER BY stock_id;

-- 23. DATABASE OBJECTS
SHOW FULL TABLES;
SHOW INDEX FROM popular_stocks;
SHOW INDEX FROM user_portfolio;
SHOW PROCEDURE STATUS WHERE Db = 'StockPortfolioDB';
SHOW FUNCTION STATUS WHERE Db = 'StockPortfolioDB';
SHOW TRIGGERS FROM StockPortfolioDB;
