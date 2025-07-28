CREATE TABLE IF NOT EXISTS buy_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(255) UNIQUE,
    market VARCHAR(20),
    created_at DATETIME,
    price FLOAT,
    volume FLOAT,
    side VARCHAR(10),
    ord_type VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS sell_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(255) UNIQUE,
    market VARCHAR(20),
    created_at DATETIME,
    price FLOAT,
    volume FLOAT,
    side VARCHAR(10),
    ord_type VARCHAR(20)
);
