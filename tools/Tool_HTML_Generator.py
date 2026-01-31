import os
from datetime import datetime
from typing import Dict, List, Optional, Union
from langchain_core.tools import tool
import plotly.graph_objects as go
import plotly.express as px
import plotly
from jinja2 import Template, Environment, FileSystemLoader
import json
import tempfile

FILE_FOLDER = tempfile.gettempdir()

def create_plotly_chart(chart_type: str, data: Dict, config: Dict) -> go.Figure:
    """
    创建Plotly图表对象
    
    Args:
        chart_type: 图表类型 (line/bar/pie/scatter/heatmap/box)
        data: 图表数据
        config: 图表配置（标题、标签等）
    
    Returns:
        Plotly图表对象
    """
    title = config.get('title', '数据可视化')
    
    if chart_type == 'line':
        fig = go.Figure()
        for series_name, series_data in data.items():
            if series_name != 'x':
                fig.add_trace(go.Scatter(
                    x=data.get('x', list(range(len(series_data)))),
                    y=series_data,
                    mode='lines+markers',
                    name=series_name
                ))
        fig.update_layout(
            title=title,
            xaxis_title=config.get('x_label', 'X轴'),
            yaxis_title=config.get('y_label', 'Y轴')
        )
    
    elif chart_type == 'bar':
        fig = go.Figure()
        for series_name, series_data in data.items():
            if series_name != 'x':
                fig.add_trace(go.Bar(
                    x=data.get('x', list(range(len(series_data)))),
                    y=series_data,
                    name=series_name
                ))
        fig.update_layout(
            title=title,
            xaxis_title=config.get('x_label', '类别'),
            yaxis_title=config.get('y_label', '数值'),
            barmode=config.get('barmode', 'group')
        )
    
    elif chart_type == 'pie':
        labels = data.get('labels', [])
        values = data.get('values', [])
        fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
        fig.update_layout(title=title)
    
    elif chart_type == 'scatter':
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data.get('x', []),
            y=data.get('y', []),
            mode='markers',
            marker=dict(
                size=data.get('size', 8),
                color=data.get('color', 'blue'),
                opacity=0.7
            ),
            text=data.get('text', None)
        ))
        fig.update_layout(
            title=title,
            xaxis_title=config.get('x_label', 'X轴'),
            yaxis_title=config.get('y_label', 'Y轴')
        )
    
    elif chart_type == 'heatmap':
        fig = go.Figure(data=go.Heatmap(
            z=data.get('z', []),
            x=data.get('x', None),
            y=data.get('y', None),
            colorscale='Viridis'
        ))
        fig.update_layout(title=title)
    
    elif chart_type == 'box':
        fig = go.Figure()
        for series_name, series_data in data.items():
            fig.add_trace(go.Box(y=series_data, name=series_name))
        fig.update_layout(
            title=title,
            yaxis_title=config.get('y_label', '数值')
        )
    
    else:
        raise ValueError(f"不支持的图表类型: {chart_type}")
    
    # 通用布局配置
    fig.update_layout(
        template=config.get('template', 'plotly_white'),
        height=config.get('height', 500),
        width=config.get('width', None),
        showlegend=config.get('showlegend', True),
        hovermode=config.get('hovermode', 'closest')
    )
    
    return fig


def get_template_loader():
    """获取Jinja2模板加载器"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(__file__))
    template_dir = os.path.join(project_root, 'templates', 'html')
    
    # 如果模板目录不存在，返回None
    if not os.path.exists(template_dir):
        return None
    
    # 创建Jinja2环境
    env = Environment(loader=FileSystemLoader(template_dir))
    return env


def load_template_from_file(dashboard_type: str = 'modern'):
    """
    从文件加载HTML模板
    
    Args:
        dashboard_type: 模板类型 (modern/classic/minimal)
    
    Returns:
        Jinja2 Template对象，如果失败返回None
    """
    try:
        env = get_template_loader()
        if env is None:
            return None
        
        template_filename = f"{dashboard_type}.html"
        template = env.get_template(template_filename)
        return template
    except Exception as e:
        print(f"⚠️ 从文件加载模板失败: {str(e)}")
        return None


def generate_html_template(dashboard_type: str = 'modern') -> str:
    """
    生成HTML模板
    
    Args:
        dashboard_type: 模板类型 (modern/classic/minimal)
    
    Returns:
        HTML模板字符串
    """
    if dashboard_type == 'modern':
        template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #2d3748;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #718096;
            font-size: 1.1em;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .chart-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .chart-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
        
        .chart-title {
            font-size: 1.3em;
            color: #2d3748;
            margin-bottom: 15px;
            font-weight: 600;
        }
        
        .footer {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
            color: #718096;
        }
        
        @media (max-width: 768px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="header">
            <h1>{{ title }}</h1>
            <p>{{ description }}</p>
            <p style="font-size: 0.9em; margin-top: 10px;">生成时间: {{ generated_time }}</p>
        </div>
        
        <div class="charts-grid">
            {% for chart in charts %}
            <div class="chart-card">
                {% if chart.title %}
                <div class="chart-title">{{ chart.title }}</div>
                {% endif %}
                <div id="chart-{{ loop.index }}"></div>
            </div>
            {% endfor %}
        </div>
        
        <div class="footer">
            <p>Powered by Plotly | 数据科学家 AI Agent 系统</p>
        </div>
    </div>
    
    <script>
        {% for chart in charts %}
        Plotly.newPlot('chart-{{ loop.index }}', 
            {{ chart.data }}, 
            {{ chart.layout }},
            {responsive: true, displayModeBar: true}
        );
        {% endfor %}
    </script>
</body>
</html>
        """
    
    elif dashboard_type == 'classic':
        template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {
            font-family: Georgia, serif;
            background: #f5f5f5;
            padding: 40px 20px;
            color: #333;
        }
        
        .dashboard-container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        h1 {
            border-bottom: 3px solid #333;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }
        
        .chart-card {
            margin-bottom: 40px;
            padding: 20px;
            border: 1px solid #ddd;
        }
        
        .chart-title {
            font-size: 1.4em;
            margin-bottom: 15px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <h1>{{ title }}</h1>
        <p>{{ description }}</p>
        <p><small>生成时间: {{ generated_time }}</small></p>
        <hr>
        
        {% for chart in charts %}
        <div class="chart-card">
            {% if chart.title %}
            <div class="chart-title">{{ chart.title }}</div>
            {% endif %}
            <div id="chart-{{ loop.index }}"></div>
        </div>
        {% endfor %}
    </div>
    
    <script>
        {% for chart in charts %}
        Plotly.newPlot('chart-{{ loop.index }}', 
            {{ chart.data }}, 
            {{ chart.layout }},
            {responsive: true}
        );
        {% endfor %}
    </script>
</body>
</html>
        """
    
    else:  # minimal
        template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .chart { margin-bottom: 30px; }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <p>{{ description }}</p>
    
    {% for chart in charts %}
    <div class="chart">
        <div id="chart-{{ loop.index }}"></div>
    </div>
    {% endfor %}
    
    <script>
        {% for chart in charts %}
        Plotly.newPlot('chart-{{ loop.index }}', {{ chart.data }}, {{ chart.layout }});
        {% endfor %}
    </script>
</body>
</html>
        """
    
    return template


@tool
def generate_dashboard_html(
    charts_config: List[Dict],
    title: str = "数据分析仪表盘",
    description: str = "基于数据分析结果生成的可视化报告",
    template_type: str = "modern",
    output_filename: Optional[str] = None,
    save_dir: Optional[str] = None
) -> str:
    """
    生成交互式数据可视化HTML页面
    
    参数:
        charts_config: 图表配置列表，每个配置包含:
            - type: 图表类型 (line/bar/pie/scatter/heatmap/box)
            - data: 图表数据字典
            - config: 图表配置（标题、标签等）
            
            示例:
            [
                {
                    "type": "line",
                    "data": {"x": [1,2,3], "销售额": [100,200,150]},
                    "config": {"title": "销售趋势", "x_label": "月份", "y_label": "金额"}
                },
                {
                    "type": "pie", 
                    "data": {"labels": ["A","B","C"], "values": [30,50,20]},
                    "config": {"title": "市场份额"}
                }
            ]
        
        title: 仪表盘标题
        description: 仪表盘描述
        template_type: 模板类型 (modern/classic/minimal)
        output_filename: 输出文件名（不指定则自动生成）
        save_dir: 保存目录（不指定则使用默认temp目录）
    
    返回:
        生成的HTML文件路径
    """
    try:
        # 准备保存目录
        if save_dir is None:
            save_dir = FILE_FOLDER
        
        os.makedirs(save_dir, exist_ok=True)
        
        # 生成文件名
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"dashboard_{timestamp}.html"
        
        if not output_filename.endswith('.html'):
            output_filename += '.html'
        
        output_path = os.path.join(save_dir, output_filename)
        
        # 生成Plotly图表
        charts_data = []
        for idx, chart_config in enumerate(charts_config):
            chart_type = chart_config.get('type', 'line')
            data = chart_config.get('data', {})
            config = chart_config.get('config', {})
            
            try:
                fig = create_plotly_chart(chart_type, data, config)
                
                # 将图表转换为JSON格式
                chart_json = {
                    'data': json.dumps(fig.data, cls=plotly.utils.PlotlyJSONEncoder),
                    'layout': json.dumps(fig.layout, cls=plotly.utils.PlotlyJSONEncoder),
                    'title': config.get('title', f'图表 {idx+1}')
                }
                charts_data.append(chart_json)
                
            except Exception as e:
                print(f"⚠️ 图表 {idx+1} 生成失败: {str(e)}")
                continue
        
        if not charts_data:
            return "❌ 错误: 没有成功生成任何图表"
        
        # 渲染HTML模板
        # 首先尝试从文件加载模板
        template = load_template_from_file(template_type)
        
        if template is None:
            # 如果文件加载失败，使用内置模板
            print(f"📝 使用内置模板: {template_type}")
            template_str = generate_html_template(template_type)
            template = Template(template_str)
        else:
            print(f"📁 使用外部模板文件: templates/html/{template_type}.html")
        
        html_content = template.render(
            title=title,
            description=description,
            generated_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            charts=charts_data
        )
        
        # 保存HTML文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML仪表盘已生成: {output_path}")
        print(f"📊 包含 {len(charts_data)} 个图表")
        print(f"🎨 模板类型: {template_type}")

        file_url = f"http://localhost:5000/files/{os.path.basename(output_path)}"
        return f"成功生成HTML仪表盘: {output_path}, 访问URL: {file_url}"
    
    except Exception as e:
        error_msg = f"❌ 生成HTML失败: {str(e)}"
        print(error_msg)
        return error_msg