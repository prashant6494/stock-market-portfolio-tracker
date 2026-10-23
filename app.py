
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from datetime import date

from db import get_connection
from market_data import get_latest_price, get_history, normalize_symbol


st.set_page_config(
    page_title="Stock Portfolio Tracker",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Stock Portfolio Tracker")
st.caption(
    "MySQL • Python • Streamlit • Yahoo Finance | "
    "Educational portfolio tracker"
)

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Choose a section",
    [
        "Dashboard",
        "Portfolio Management",
        "Stock Catalogue",
        "Technical Charts"
    ]
)


def read_sql(query, params=None):
    conn = get_connection()
    try:
        return pd.read_sql(query, conn, params=params)
    finally:
        conn.close()


def execute_sql(query, params=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return cursor.rowcount, cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_stocks():
    return read_sql("""
        SELECT stock_id, stock_name, stock_symbol, sector,
               current_price, price_date
        FROM popular_stocks
        ORDER BY stock_name
    """)


def get_holdings(user_name=None):
    query = """
        SELECT
            p.portfolio_id, p.user_name, p.stock_id,
            s.stock_name, s.stock_symbol, s.sector,
            p.buying_price, p.quantity, p.buy_date, p.notes,
            s.current_price, s.price_date
        FROM user_portfolio p
        JOIN popular_stocks s ON p.stock_id = s.stock_id
    """
    params = None

    if user_name:
        query += " WHERE p.user_name = %s"
        params = (user_name,)

    query += " ORDER BY p.buy_date DESC, p.portfolio_id DESC"
    return read_sql(query, params)


def refresh_price(stock_id, symbol):
    price, timestamp = get_latest_price(symbol)

    if price is None:
        return False

    execute_sql("""
        UPDATE popular_stocks
        SET current_price = %s, price_date = %s
        WHERE stock_id = %s
    """, (price, timestamp, int(stock_id)))

    return True


def refresh_all_prices():
    stocks = get_stocks()
    updated = []
    failed = []

    for _, stock in stocks.iterrows():
        try:
            if refresh_price(stock["stock_id"], stock["stock_symbol"]):
                updated.append(stock["stock_symbol"])
            else:
                failed.append(stock["stock_symbol"])
        except Exception:
            failed.append(stock["stock_symbol"])

    return updated, failed


def add_stock(name, symbol, sector):
    name = name.strip()
    symbol = normalize_symbol(symbol)
    sector = sector.strip() or "Not specified"

    if not name or not symbol:
        raise ValueError("Company name and ticker are required.")

    execute_sql("""
        INSERT INTO popular_stocks
            (stock_name, stock_symbol, sector)
        VALUES (%s, %s, %s)
    """, (name, symbol, sector))


def add_holding(user, stock_id, buy_price, quantity, buy_date, notes):
    if not user.strip():
        raise ValueError("Enter a user name.")
    if buy_price <= 0 or quantity <= 0:
        raise ValueError("Buying price and quantity must be positive.")

    execute_sql("""
        INSERT INTO user_portfolio
            (user_name, stock_id, buying_price, quantity, buy_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        user.strip(), int(stock_id), float(buy_price),
        int(quantity), buy_date, notes.strip() or None
    ))


def delete_holding(portfolio_id):
    return execute_sql("""
        DELETE FROM user_portfolio
        WHERE portfolio_id = %s
    """, (int(portfolio_id),))[0]


def delete_stock(stock_id):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM user_portfolio
            WHERE stock_id = %s
        """, (int(stock_id),))

        linked = int(cursor.fetchone()[0])

        if linked:
            return False, linked

        cursor.execute("""
            DELETE FROM popular_stocks
            WHERE stock_id = %s
        """, (int(stock_id),))

        conn.commit()
        return cursor.rowcount > 0, 0

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def calculate_portfolio(data):
    data = data.copy()

    data["invested"] = data["buying_price"] * data["quantity"]
    data["current_value"] = (
        data["current_price"] * data["quantity"]
    )
    data["profit_loss"] = data["current_value"] - data["invested"]

    data["return_percent"] = (
        (data["current_price"] - data["buying_price"])
        / data["buying_price"] * 100
    )

    return data


def money(value):
    if pd.isna(value):
        return "Unavailable"
    return f"₹{value:,.2f}"


def stock_label(row):
    return f"{row['stock_name']} ({row['stock_symbol']})"


# ---------------- DASHBOARD ----------------

if page == "Dashboard":
    st.subheader("Market Overview")

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("🔄 Refresh all stock prices"):
            with st.spinner("Fetching latest available prices..."):
                updated, failed = refresh_all_prices()

            st.success(f"Updated prices for {len(updated)} stocks.")

            if failed:
                st.warning("Unavailable: " + ", ".join(failed))

            st.rerun()

    with col2:
        st.caption(
            "Prices depend on Yahoo Finance availability and may be delayed. "
            "Refresh manually to request updated quotes."
        )

    try:
        stocks = get_stocks()
        holdings = get_holdings()

        invested = 0.0
        current_value = None
        pnl = None

        if not holdings.empty:
            holdings = calculate_portfolio(holdings)
            invested = float(holdings["invested"].sum())

            # Do not treat missing prices as zero.
            known = holdings["current_value"].notna()

            if known.all():
                current_value = float(holdings["current_value"].sum())
                pnl = current_value - invested
            elif known.any():
                current_value = float(
                    holdings.loc[known, "current_value"].sum()
                )
                pnl = current_value - invested

        a, b, c, d = st.columns(4)
        a.metric("Stocks in Catalogue", len(stocks))
        b.metric("Portfolio Holdings", len(holdings))
        c.metric("Total Invested", money(invested))

        if current_value is None:
            d.metric("Portfolio P&L", "Unavailable")
        else:
            d.metric(
                "Portfolio P&L",
                money(pnl),
                delta=(
                    f"{pnl / invested * 100:.2f}%"
                    if invested else "0.00%"
                )
            )

        st.subheader("Stock Watchlist")

        if not stocks.empty:
            st.dataframe(
                stocks[
                    [
                        "stock_name", "stock_symbol", "sector",
                        "current_price", "price_date"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

        if not holdings.empty:
            st.subheader("Portfolio Allocation")

            allocation = (
                holdings.groupby("stock_name", as_index=False)["invested"]
                .sum()
            )

            fig = go.Figure(
                go.Pie(
                    labels=allocation["stock_name"],
                    values=allocation["invested"],
                    hole=0.45
                )
            )
            fig.update_layout(
                title="Allocation by Invested Amount",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Dashboard error: {e}")


# ---------------- PORTFOLIO MANAGEMENT ----------------

elif page == "Portfolio Management":
    st.subheader("Add a Portfolio Holding")

    try:
        stocks = get_stocks()

        if stocks.empty:
            st.warning("Add a stock in Stock Catalogue first.")
        else:
            stocks["label"] = stocks.apply(stock_label, axis=1)

            with st.form("add_holding_form", clear_on_submit=True):
                user_name = st.selectbox(
                    "Select user",
                    [
                        "Demo User 1",
                        "Demo User 2",
                        "Demo User 3",
                        "Other user"
                    ]
                )

                if user_name == "Other user":
                    actual_user = st.text_input("Enter user name")
                else:
                    actual_user = user_name

                selected_label = st.selectbox(
                    "Stock",
                    stocks["label"].tolist()
                )

                selected_stock = stocks[
                    stocks["label"] == selected_label
                ].iloc[0]

                buy_price = st.number_input(
                    "Buying price per share (₹)",
                    min_value=0.01,
                    value=100.0,
                    step=1.0
                )

                quantity = st.number_input(
                    "Quantity",
                    min_value=1,
                    value=1,
                    step=1
                )

                buy_date = st.date_input(
                    "Purchase date",
                    value=date.today()
                )

                notes = st.text_input("Notes (optional)")

                submitted = st.form_submit_button("Save holding")

            if submitted:
                try:
                    add_holding(
                        actual_user,
                        selected_stock["stock_id"],
                        buy_price,
                        quantity,
                        buy_date,
                        notes
                    )
                    st.success("Holding saved successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not save holding: {e}")

        st.divider()
        st.subheader("View and Delete Holdings")

        users = read_sql("""
            SELECT DISTINCT user_name
            FROM user_portfolio
            ORDER BY user_name
        """)

        if users.empty:
            st.info("No portfolio holdings found.")
        else:
            user_options = ["All users"] + users["user_name"].tolist()
            selected_user = st.selectbox(
                "Filter holdings by user",
                user_options
            )

            selected_filter = (
                None if selected_user == "All users"
                else selected_user
            )

            holdings = get_holdings(selected_filter)

            if not holdings.empty:
                holdings = calculate_portfolio(holdings)

                st.dataframe(
                    holdings[
                        [
                            "portfolio_id", "user_name", "stock_name",
                            "buying_price", "quantity", "buy_date",
                            "invested", "current_price",
                            "current_value", "profit_loss",
                            "return_percent"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

                holdings["delete_label"] = (
                    "ID " + holdings["portfolio_id"].astype(str)
                    + " | " + holdings["user_name"]
                    + " | " + holdings["stock_name"]
                    + " | Qty " + holdings["quantity"].astype(str)
                )

                selected_delete = st.selectbox(
                    "Choose a holding to delete",
                    holdings["delete_label"].tolist()
                )

                delete_row = holdings[
                    holdings["delete_label"] == selected_delete
                ].iloc[0]

                confirm = st.checkbox(
                    "I confirm deletion of this portfolio holding"
                )

                if st.button(
                    "Delete selected holding",
                    disabled=not confirm
                ):
                    try:
                        count = delete_holding(
                            delete_row["portfolio_id"]
                        )
                        if count:
                            st.success("Holding deleted.")
                            st.rerun()
                        else:
                            st.warning("Holding was not found.")
                    except Exception as e:
                        st.error(f"Delete failed: {e}")

    except Exception as e:
        st.error(f"Portfolio error: {e}")


# ---------------- STOCK CATALOGUE ----------------

elif page == "Stock Catalogue":
    st.subheader("Add a Stock")

    with st.form("add_stock_form", clear_on_submit=True):
        name = st.text_input(
            "Company name",
            placeholder="Bharat Electronics Limited"
        )
        symbol = st.text_input(
            "Ticker",
            placeholder="BEL or BEL.NS"
        )
        sector = st.text_input("Sector", placeholder="Defence")
        add_clicked = st.form_submit_button("Add stock")

    if add_clicked:
        try:
            add_stock(name, symbol, sector)
            st.success("Stock added to catalogue.")
            st.rerun()
        except Exception as e:
            st.error(
                "Could not add stock. Check whether the ticker already "
                f"exists. Details: {e}"
            )

    st.divider()
    st.subheader("Current Stock Catalogue")

    try:
        stocks = get_stocks()

        st.dataframe(
            stocks,
            use_container_width=True,
            hide_index=True
        )

        if not stocks.empty:
            stocks["label"] = stocks.apply(stock_label, axis=1)
            chosen = st.selectbox(
                "Choose stock to remove",
                stocks["label"].tolist()
            )

            selected = stocks[stocks["label"] == chosen].iloc[0]

            st.warning(
                "A stock with saved portfolio holdings cannot be deleted. "
                "Remove its holdings first if deletion is intended."
            )

            confirm_stock = st.checkbox(
                "I confirm removal from the catalogue"
            )

            if st.button(
                "Remove stock",
                disabled=not confirm_stock
            ):
                try:
                    removed, linked = delete_stock(
                        selected["stock_id"]
                    )

                    if removed:
                        st.success("Stock removed.")
                        st.rerun()
                    elif linked:
                        st.error(
                            f"This stock has {linked} linked holding(s). "
                            "Delete those holdings first if appropriate."
                        )
                    else:
                        st.warning("Stock was not found.")

                except Exception as e:
                    st.error(f"Could not remove stock: {e}")

    except Exception as e:
        st.error(f"Catalogue error: {e}")


# ---------------- TECHNICAL CHARTS ----------------

else:
    st.subheader("Technical Charts & Analysis")

    st.caption(
        "Interactive charting inspired by TradingView. Market data is "
        "provided by Yahoo Finance, not a guaranteed real-time feed."
    )

    try:
        stocks = get_stocks()

        if stocks.empty:
            st.warning("Add a stock to the catalogue first.")
        else:
            stocks["label"] = stocks.apply(stock_label, axis=1)

            selected_label = st.selectbox(
                "Select stock",
                stocks["label"].tolist()
            )

            stock = stocks[
                stocks["label"] == selected_label
            ].iloc[0]

            c1, c2, c3 = st.columns(3)

            with c1:
                period = st.selectbox(
                    "Period",
                    ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
                    index=2
                )

            with c2:
                interval = st.selectbox(
                    "Interval",
                    ["1d", "1wk", "1mo"],
                    index=0
                )

            with c3:
                chart_type = st.selectbox(
                    "Chart type",
                    ["Candlestick", "Line", "OHLC"]
                )

            indicators = st.multiselect(
                "Indicators",
                [
                    "SMA 20",
                    "SMA 50",
                    "SMA 200",
                    "EMA 20",
                    "Bollinger Bands"
                ],
                default=["SMA 20", "SMA 50"]
            )

            with st.spinner("Loading price history..."):
                history = get_history(
                    stock["stock_symbol"],
                    period=period,
                    interval=interval
                )

            if history.empty:
                st.warning(
                    "No history returned. Check the ticker, internet "
                    "connection, or selected period."
                )
            else:
                close = history["Close"]

                latest = float(close.iloc[-1])
                previous = (
                    float(close.iloc[-2])
                    if len(close) > 1 else latest
                )
                change_pct = (
                    (latest - previous) / previous * 100
                    if previous else 0
                )

                k1, k2, k3, k4 = st.columns(4)

                k1.metric(
                    "Latest close",
                    f"₹{latest:,.2f}",
                    f"{change_pct:+.2f}%"
                )
                k2.metric(
                    "Period high",
                    f"₹{history['High'].max():,.2f}"
                )
                k3.metric(
                    "Period low",
                    f"₹{history['Low'].min():,.2f}"
                )
                k4.metric(
                    "Data points",
                    len(history)
                )

                fig = go.Figure()

                if chart_type == "Candlestick":
                    fig.add_trace(go.Candlestick(
                        x=history.index,
                        open=history["Open"],
                        high=history["High"],
                        low=history["Low"],
                        close=history["Close"],
                        name="Price"
                    ))

                elif chart_type == "OHLC":
                    fig.add_trace(go.Ohlc(
                        x=history.index,
                        open=history["Open"],
                        high=history["High"],
                        low=history["Low"],
                        close=history["Close"],
                        name="OHLC"
                    ))

                else:
                    fig.add_trace(go.Scatter(
                        x=history.index,
                        y=close,
                        mode="lines",
                        name="Close"
                    ))

                if "SMA 20" in indicators:
                    fig.add_trace(go.Scatter(
                        x=history.index,
                        y=close.rolling(20).mean(),
                        name="SMA 20"
                    ))

                if "SMA 50" in indicators:
                    fig.add_trace(go.Scatter(
                        x=history.index,
                        y=close.rolling(50).mean(),
                        name="SMA 50"
                    ))

                if "SMA 200" in indicators:
                    fig.add_trace(go.Scatter(
                        x=history.index,
                        y=close.rolling(200).mean(),
                        name="SMA 200"
                    ))

                if "EMA 20" in indicators:
                    fig.add_trace(go.Scatter(
                        x=history.index,
                        y=close.ewm(span=20, adjust=False).mean(),
                        name="EMA 20"
                    ))

                if "Bollinger Bands" in indicators:
                    middle = close.rolling(20).mean()
                    deviation = close.rolling(20).std()

                    fig.add_trace(go.Scatter(
                        x=history.index,
                        y=middle + 2 * deviation,
                        name="Bollinger Upper",
                        line=dict(dash="dot")
                    ))

                    fig.add_trace(go.Scatter(
                        x=history.index,
                        y=middle - 2 * deviation,
                        name="Bollinger Lower",
                        line=dict(dash="dot")
                    ))

                fig.update_layout(
                    title=selected_label,
                    template="plotly_dark",
                    height=650,
                    xaxis_title="Date",
                    yaxis_title="Price (₹)",
                    hovermode="x unified",
                    xaxis_rangeslider_visible=True,
                    legend=dict(orientation="h")
                )

                fig.update_xaxes(
                    showspikes=True,
                    spikemode="across",
                    spikesnap="cursor"
                )

                fig.update_yaxes(
                    showspikes=True,
                    spikemode="across",
                    spikesnap="cursor"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={
                        "scrollZoom": True,
                        "displaylogo": False,
                        "responsive": True
                    }
                )

                if "Volume" in history.columns:
                    volume_fig = go.Figure()
                    volume_fig.add_trace(go.Bar(
                        x=history.index,
                        y=history["Volume"],
                        name="Volume"
                    ))
                    volume_fig.update_layout(
                        title="Trading Volume",
                        template="plotly_dark",
                        height=250
                    )
                    st.plotly_chart(
                        volume_fig,
                        use_container_width=True
                    )

                if st.button("Save latest available price to MySQL"):
                    try:
                        if refresh_price(
                            stock["stock_id"],
                            stock["stock_symbol"]
                        ):
                            st.success("Price saved to MySQL.")
                            st.rerun()
                        else:
                            st.warning("Price was unavailable.")
                    except Exception as e:
                        st.error(f"Could not save price: {e}")

                st.caption(
                    "Moving averages and Bollinger Bands are historical "
                    "indicators, not guaranteed trading signals. P&L does "
                    "not include taxes, brokerage or other charges."
                )

    except Exception as e:
        st.error(f"Chart error: {e}")
