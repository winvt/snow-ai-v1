"""
Reusable chart functions for the Loyverse Dashboard
Reduces code duplication and ensures consistent styling
"""
import plotly.express as px
import pandas as pd


def create_sales_bar_chart(df, group_by, title, color_scale="Blues", orientation="h"):
    """
    Create a horizontal bar chart for sales analysis
    
    Args:
        df: DataFrame with data
        group_by: Column name to group by
        title: Chart title
        color_scale: Plotly color scale (default: Blues)
        orientation: 'h' for horizontal, 'v' for vertical
    """
    data = df.groupby(group_by)["total"].sum().reset_index()
    data.columns = [group_by, "Total Sales"]
    data = data.sort_values("Total Sales", ascending=False)
    
    if orientation == "h":
        fig = px.bar(data, x="Total Sales", y=group_by,
                    orientation="h", title=title,
                    color="Total Sales",
                    color_continuous_scale=color_scale,
                    text_auto=True)
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
    else:
        fig = px.bar(data, x=group_by, y="Total Sales",
                    title=title,
                    color="Total Sales",
                    color_continuous_scale=color_scale,
                    text_auto=True)
        fig.update_traces(textposition='outside')
    
    return fig


def create_sales_pie_chart(df, group_by, title, hole=0.4, color_sequence=None):
    """
    Create a pie/donut chart for sales distribution
    
    Args:
        df: DataFrame with data
        group_by: Column name to group by
        title: Chart title
        hole: Size of center hole (0 for pie, 0.4 for donut)
        color_sequence: Plotly color sequence
    """
    data = df.groupby(group_by)["total"].sum().reset_index()
    data.columns = [group_by, "Total Sales"]
    
    kwargs = {
        "data_frame": data,
        "names": group_by,
        "values": "Total Sales",
        "title": title,
        "hole": hole
    }
    
    if color_sequence:
        kwargs["color_discrete_sequence"] = color_sequence
    
    fig = px.pie(**kwargs)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    
    return fig


def create_trend_line_chart(df, x_col, y_col, color_col=None, title="Trend Analysis"):
    """
    Create a line chart for trend analysis
    
    Args:
        df: DataFrame with data
        x_col: Column for x-axis (usually date)
        y_col: Column for y-axis (usually sales)
        color_col: Optional column for multiple lines
        title: Chart title
    """
    kwargs = {
        "data_frame": df,
        "x": x_col,
        "y": y_col,
        "title": title,
        "markers": True
    }
    
    if color_col:
        kwargs["color"] = color_col
    
    fig = px.line(**kwargs)
    return fig


def create_aggregated_table(df, group_by, agg_funcs=None):
    """
    Create aggregated summary table
    
    Args:
        df: DataFrame with data
        group_by: Column(s) to group by
        agg_funcs: Dictionary of aggregation functions
                  Default: sum total, sum quantity, count bills, count customers
    """
    if agg_funcs is None:
        agg_funcs = {
            "total": "sum",
            "quantity": "sum",
            "bill_number": "nunique",
            "customer_id": "nunique"
        }
    
    result = df.groupby(group_by).agg(agg_funcs).reset_index()
    
    # Rename columns to human-readable names
    column_mapping = {
        "total": "Total Sales",
        "quantity": "Items Sold",
        "bill_number": "Transactions",
        "customer_id": "Unique Customers"
    }
    
    new_cols = []
    for col in result.columns:
        if col in column_mapping:
            new_cols.append(column_mapping[col])
        else:
            new_cols.append(col.replace("_", " ").title())
    
    result.columns = new_cols
    return result


def create_histogram(df, column, title, bins=20, color="#636EFA"):
    """
    Create a histogram for distribution analysis
    
    Args:
        df: DataFrame with data
        column: Column to analyze
        title: Chart title
        bins: Number of bins
        color: Bar color
    """
    fig = px.histogram(df, x=column,
                      title=title,
                      nbins=bins,
                      color_discrete_sequence=[color])
    return fig


def create_scatter_plot(df, x_col, y_col, size_col=None, color_col=None, 
                       hover_data=None, title="Scatter Plot"):
    """
    Create a scatter plot for correlation analysis
    
    Args:
        df: DataFrame with data
        x_col: Column for x-axis
        y_col: Column for y-axis
        size_col: Optional column for bubble size
        color_col: Optional column for color
        hover_data: Optional list of columns to show on hover
        title: Chart title
    """
    kwargs = {
        "data_frame": df,
        "x": x_col,
        "y": y_col,
        "title": title
    }
    
    if size_col:
        kwargs["size"] = size_col
    if color_col:
        kwargs["color"] = color_col
        kwargs["color_continuous_scale"] = "Rainbow"
    if hover_data:
        kwargs["hover_data"] = hover_data
    
    fig = px.scatter(**kwargs)
    return fig


def create_daily_sales_summary(df):
    """
    Create comprehensive daily sales summary
    
    Args:
        df: DataFrame with 'day', 'total', 'quantity', 'bill_number' columns
    
    Returns:
        DataFrame with daily aggregates
    """
    daily = df.groupby("day").agg({
        "total": "sum",
        "quantity": "sum",
        "bill_number": "count"
    }).reset_index()
    daily.columns = ["Date", "Total Sales", "Items Sold", "Transactions"]
    return daily


def create_top_n_analysis(df, group_by, metric="total", n=10, title_prefix="Top"):
    """
    Create top N analysis (products, customers, locations, etc.)
    
    Args:
        df: DataFrame with data
        group_by: Column to group by
        metric: Metric to sort by (default: total)
        n: Number of top items to show
        title_prefix: Prefix for chart title
    
    Returns:
        tuple: (aggregated_df, bar_chart_figure)
    """
    agg_data = df.groupby(group_by).agg({
        "total": "sum",
        "quantity": "sum",
        "bill_number": "nunique"
    }).reset_index()
    agg_data.columns = [group_by, "Total Sales", "Quantity Sold", "Times Ordered"]
    agg_data = agg_data.sort_values("Total Sales", ascending=False).head(n)
    
    fig = create_sales_bar_chart(
        df.head(len(agg_data)),
        group_by=group_by,
        title=f"{title_prefix} {n} by Sales",
        color_scale="Viridis"
    )
    
    return agg_data, fig


def style_dataframe_metric(value, format_type="currency"):
    """
    Format metric values for display
    
    Args:
        value: Numeric value to format
        format_type: 'currency', 'number', 'percent'
    
    Returns:
        Formatted string
    """
    if format_type == "currency":
        return f"{value:,.0f}"
    elif format_type == "number":
        return f"{value:,.0f}"
    elif format_type == "percent":
        return f"{value:.1%}"
    else:
        return str(value)

