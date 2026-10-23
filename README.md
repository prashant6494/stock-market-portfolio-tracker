# Stock Portfolio Tracker

A Python-based stock portfolio management application built with Streamlit and MySQL. The project helps users manage stock holdings, track investment values, calculate profit and loss, view market prices, and analyze historical stock charts.

## Project Overview

The Stock Portfolio Tracker provides a dashboard for organizing stock investments and monitoring portfolio performance. It combines a MySQL database for persistent storage, Python for application logic, Streamlit for the user interface, and Yahoo Finance data through `yfinance` for market information.

This is an educational portfolio management project and is not a brokerage or trading platform.

## Features

- **Portfolio Dashboard:** View portfolio holdings, investment summaries, and performance metrics.
- **Portfolio Management:** Add holdings with purchase price, quantity, purchase date, and notes.
- **Profit and Loss Analysis:** Calculate investment value, profit or loss, and percentage returns when market prices are available.
- **Stock Catalogue:** View available stocks and add or remove catalogue entries, subject to database relationships.
- **Market Price Updates:** Retrieve available stock prices using Yahoo Finance.
- **Technical Charts:** View historical stock price charts using Plotly.
- **Technical Indicators:** Analyze charts using moving averages, exponential moving averages, and Bollinger Bands, where implemented.
- **MySQL Database:** Store stock information, holdings, price audit records, and portfolio summaries.
- **Multiple Themes:** Customize the dashboard appearance using the available themes.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Application logic |
| Streamlit | Interactive web interface |
| MySQL | Database and persistent storage |
| Pandas | Data processing |
| yfinance | Stock market data retrieval |
| Plotly | Interactive financial charts |
| mysql-connector-python | Python–MySQL connectivity |
| Git and GitHub | Version control and project hosting |

## Project Structure

```text
STOCK MARKET/
├── app.py
├── db.py
├── market_data.py
├── theme.py
├── requirements.txt
├── .gitignore
├── .streamlit/
│   └── secrets.toml
└── database.sql
```

The SQL filename above is an example; use the actual filename of your database script.

## Database Design

The project database is named `StockPortfolioDB`.

The principal tables are:

- `popular_stocks` — stores stock names, symbols, sectors, and market prices.
- `user_portfolio` — stores user holdings, purchase prices, quantities, dates, and notes.
- `price_audit` — records changes to stock prices.
- `stock_summary` — stores summarized investment quantities and invested amounts.

The database also includes a portfolio view, a profit-and-loss function, stored procedures, a price-update trigger, and indexes, where configured by the SQL script.

## Prerequisites

Install the following before running the application:

- Python 3
- MySQL Server
- Git, if you want to clone the repository
- A code editor such as Visual Studio Code

## Installation and Setup

### 1. Clone the repository

Replace `YOUR_USERNAME` with your GitHub username.

```bash
git clone https://github.com/YOUR_USERNAME/stock-portfolio-tracker.git
cd stock-portfolio-tracker
```

Alternatively, download the repository ZIP file from GitHub and extract it.

### 2. Create a virtual environment

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure MySQL

Start MySQL Server and execute your project's SQL script using MySQL Workbench or the MySQL client.

Ensure that the `StockPortfolioDB` database and its required tables, views, functions, procedures, and triggers are created.

### 5. Configure database credentials

Create a file at `.streamlit/secrets.toml`:

```toml
[mysql]
host = "127.0.0.1"
port = 3306
user = "root"
password = "YOUR_MYSQL_PASSWORD"
```

Replace the placeholder with your local MySQL password.

**Security:** Never commit your actual `secrets.toml` file or database password to GitHub. Keep it excluded through `.gitignore`.

### 6. Run the application

```bash
python -m streamlit run app.py
```

Open the local URL printed in your terminal, typically:

```text
http://localhost:8501
```

## Market Data

The application uses Yahoo Finance data through the `yfinance` Python library. Data availability, update frequency, and delays depend on the symbol, exchange, and data provider.

Market prices may be unavailable or delayed. This application should not be treated as a source of guaranteed real-time prices or financial advice.

## Screenshots

Add screenshots of the following pages after running the application:

1. Main dashboard and portfolio metrics
2. Portfolio management page
3. Stock catalogue
4. Technical charts and indicators
5. Theme selector

Store screenshots in a `screenshots/` directory and embed them using Markdown. For example:

```markdown
![Dashboard](screenshots/dashboard.png)
```

## Limitations

- Market data depends on the availability of the external data provider.
- Database credentials must be configured locally.
- This project is an educational portfolio tracker, not a broker-integrated trading system.
- User selection in the current application should not be considered secure authentication unless a proper authentication system is implemented.

## Future Improvements

- Add secure user authentication and role-based access.
- Integrate additional market data providers.
- Add portfolio performance charts and benchmark comparisons.
- Implement price alerts and watchlists.
- Add exportable portfolio reports.
- Add automated testing and deployment.

## License

Choose a license before distributing or reusing the project. If you want others to use and modify your code openly, consider the MIT License.

## Author

Developed as an educational software project demonstrating Python application development, relational database design, financial data processing, and interactive dashboard development.
