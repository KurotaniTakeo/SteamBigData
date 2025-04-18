import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Pie


def load_data(csv_path):
    """加载游戏平台数据"""
    df = pd.read_csv(csv_path)

    # 确保平台字段是布尔类型
    platform_cols = ["platforms_windows", "platforms_mac", "platforms_linux"]
    for col in platform_cols:
        if col in df.columns:
            df[col] = df[col].astype(bool)

    return df


def create_platform_distribution_chart(df):
    """创建平台适配分布饼图"""

    # 生成平台组合标签
    def get_platform_label(row):
        platforms = []
        if row["platforms_windows"]:
            platforms.append("Windows")
        if row["platforms_mac"]:
            platforms.append("Mac")
        if row["platforms_linux"]:
            platforms.append("Linux")

        if not platforms:
            return "无平台支持"
        return " + ".join(platforms)

    df["platform_combination"] = df.apply(get_platform_label, axis=1)

    # 统计各组合的数量
    platform_counts = df["platform_combination"].value_counts().reset_index()
    platform_counts.columns = ["combination", "count"]

    # 准备图表数据
    data = [
        (row["combination"], row["count"])
        for _, row in platform_counts.iterrows()
    ]

    chart = (
        Pie()
        .add(
            "",
            data,
            radius=["30%", "70%"],
            label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Steam游戏平台适配分布"),
            legend_opts=opts.LegendOpts(
                orient="vertical",
                pos_top="15%",
                pos_left="2%",
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="item",
                formatter="{a} <br/>{b}: {c} ({d}%)"
            ),
        )
        .set_series_opts(
            tooltip_opts=opts.TooltipOpts(
                trigger="item",
                formatter="{a} <br/>{b}: {c} ({d}%)"
            ),
        )
    )

    return chart


if __name__ == "__main__":
    try:
        # 加载数据
        df = load_data("../../dataset/steam_games_data.csv")  # 替换为你的CSV文件路径

        # 生成图表
        chart = create_platform_distribution_chart(df)
        chart.render("game_platform_distribution.html")
        print("平台适配分布图已生成: game_platform_distribution.html")

    except Exception as e:
        print(f"处理出错: {str(e)}")
