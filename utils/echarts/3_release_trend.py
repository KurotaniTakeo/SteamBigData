import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Line


def load_data(csv_path):
    """加载已清洗的数据"""
    df = pd.read_csv(csv_path)

    # 只保留有效的发布年份（已清洗的数据应该只有有效年份或"unpublished"）
    df = df[df['release_date'] != "unpublished"]

    # 从release_date提取年份（格式应为"YYYY"或"YYYY-MM-DD"）
    df['release_year'] = df['release_date'].str.extract(r'(\d{4})')[0]

    # 删除NaN值并转换为整数
    df = df.dropna(subset=['release_year'])
    df['release_year'] = df['release_year'].astype(int)

    return df


def create_release_trend_chart(df):
    """创建发布趋势图"""
    # 按年份统计游戏数量
    year_count = df['release_year'].value_counts().sort_index().reset_index()
    year_count.columns = ['year', 'count']

    # 准备图表数据
    years = [str(int(row['year'])) for _, row in year_count.iterrows()]
    counts = [int(row['count']) for _, row in year_count.iterrows()]

    chart = (
        Line()
        .add_xaxis(years)
        .add_yaxis(
            "游戏数量",
            counts,
            is_smooth=True,
            symbol="circle",
            symbol_size=8,
            linestyle_opts=opts.LineStyleOpts(width=3),
            label_opts=opts.LabelOpts(is_show=False),
            areastyle_opts=opts.AreaStyleOpts(opacity=0.2)
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Steam游戏年度发布趋势"),
            xaxis_opts=opts.AxisOpts(
                name="年份",
                axislabel_opts=opts.LabelOpts(rotate=45)),
            yaxis_opts=opts.AxisOpts(name="发布数量"),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                formatter="{b}年: {c}款游戏"),
            datazoom_opts=[opts.DataZoomOpts()]
        )
    )

    return chart


if __name__ == "__main__":
    try:
        # 加载已清洗的数据
        df = load_data("../../dataset/steam_games_data.csv")

        # 生成图表
        chart = create_release_trend_chart(df)
        chart.render("game_release_trend.html")
        print("发布趋势图已生成: game_release_trend.html")

    except Exception as e:
        print(f"处理出错: {str(e)}")