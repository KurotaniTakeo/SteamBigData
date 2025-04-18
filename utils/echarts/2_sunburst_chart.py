import pandas as pd
import numpy as np
from pyecharts import options as opts
from pyecharts.charts import Bar
from datetime import datetime


def load_data(csv_path):
    df = pd.read_csv(csv_path)
    # 处理recommendations字段，N/A视为0，其他非数字项忽略
    df['recommendations'] = pd.to_numeric(df['recommendations'], errors='coerce').fillna(0)

    # 提取年份
    df['release_year'] = df['release_date'].apply(
        lambda x: (datetime.strptime(x.strip('"'), "%b %d, %Y").year
                   if isinstance(x, str) and ',' in x
                   else int(x) if str(x).isdigit() and len(str(x)) == 4
        else np.nan)
    )
    return df.dropna(subset=['release_year'])


def create_stacked_bar_chart(df):
    # 按年份分组计算推荐数总和
    year_recommend = df.groupby('release_year')['recommendations'].sum().reset_index()
    year_recommend = year_recommend.sort_values('release_year')

    # 准备数据
    years = [str(int(year)) for year in year_recommend['release_year']]
    recommendations = [int(recom) for recom in year_recommend['recommendations']]

    # 创建柱状图
    bar = (
        Bar(init_opts=opts.InitOpts(width="1200px", height="600px"))
        .add_xaxis(years)
        .add_yaxis(
            series_name="推荐数",
            y_axis=recommendations,
            stack="stack1",
            label_opts=opts.LabelOpts(
                position="top",
                formatter="{b}\n{c}"
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="不同年份发布的游戏热度（推荐数总和）"),
            xaxis_opts=opts.AxisOpts(
                axislabel_opts=opts.LabelOpts(rotate=-45),
                type_="category"
            ),
            yaxis_opts=opts.AxisOpts(
                name="推荐数总和",
                name_location="middle",
                name_gap=40
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="shadow"
            ),
            datazoom_opts=[opts.DataZoomOpts()]  # 添加数据缩放功能
        )
    )
    return bar


if __name__ == "__main__":
    csv_path = "../../dataset/steam_games_data.csv"  # 请替换为实际文件名
    try:
        df = load_data(csv_path)
        chart = create_stacked_bar_chart(df)
        chart.render("recommendation_bar_chart.html")
        print("柱状图已生成: recommendation_bar_chart.html")
    except Exception as e:
        print(f"处理出错: {str(e)}")