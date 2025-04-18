import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Line
import numpy as np


# 1. 从CSV文件读取并清洗价格数据
def fetch_game_prices_from_csv(csv_path):
    df = pd.read_csv(csv_path)
    prices = []

    for price_str in df["price"]:
        # 处理空值和非字符串
        if pd.isna(price_str) or price_str == "{}":
            continue

        # 处理Free情况
        if isinstance(price_str, str) and price_str.lower() == "free":
            prices.append(0.0)
            continue

        # 处理带美元符号的价格
        if isinstance(price_str, str) and price_str.startswith("$"):
            try:
                price_num = float(price_str.replace("$", "").strip())
                prices.append(price_num)
            except ValueError:
                continue

        # 处理已经是数字的情况
        elif isinstance(price_str, (int, float)):
            prices.append(float(price_str))

    return prices


# 2. 分析价格分布（按自定义区间分段）
def analyze_price_distribution(prices):
    bins = [0, 1, 10, 30, 60, 100, float('inf')]
    labels = ["Free", "<$1", "$1~10", "$10~30", "$30~60", "$60~100", ">$100"]

    counts, _ = np.histogram(prices, bins=bins)
    return labels, counts.tolist()


# 3. 生成ECharts面积图表
def generate_price_chart(labels, counts):
    line = (
        Line()
        .add_xaxis(xaxis_data=labels)
        .add_yaxis(
            series_name="游戏数量",
            y_axis=counts,
            is_smooth=True,  # 启用平滑曲线
            areastyle_opts=opts.AreaStyleOpts(opacity=0.5),  # 设置面积样式
            label_opts=opts.LabelOpts(is_show=True),  # 显示数据标签
            linestyle_opts=opts.LineStyleOpts(width=3),  # 线条加粗
            symbol="circle",  # 数据点显示为圆形
            symbol_size=8,  # 数据点大小
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Steam游戏价格分布（美元）"),
            xaxis_opts=opts.AxisOpts(
                name="价格区间",
                axislabel_opts=opts.LabelOpts(rotate=15),
                boundary_gap=False  # 让曲线从Y轴开始
            ),
            yaxis_opts=opts.AxisOpts(name="数量"),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross"  # 显示十字准星指示器
            ),
        )
        .set_series_opts(
            markpoint_opts=opts.MarkPointOpts(
                data=[
                    opts.MarkPointItem(type_="max", name="最大值"),
                    opts.MarkPointItem(type_="min", name="最小值")
                ]
            )
        )
    )
    return line


# 主流程
if __name__ == "__main__":
    csv_path = "../../dataset/steam_games_data.csv"

    try:
        prices = fetch_game_prices_from_csv(csv_path)
        labels, counts = analyze_price_distribution(prices)

        chart = generate_price_chart(labels, counts)
        output_file = "steam_price_distribution_line.html"
        chart.render(output_file)
        print(f"图表已生成：{output_file}")

    except FileNotFoundError:
        print(f"错误：文件 {csv_path} 不存在！")
    except Exception as e:
        print(f"发生错误：{str(e)}")