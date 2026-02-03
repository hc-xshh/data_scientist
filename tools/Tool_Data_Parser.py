import os
from pathlib import Path
from typing import Dict, List, Any
import json
import tempfile
from urllib.parse import urlparse
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# 安装依赖: pip install pandas openpyxl
try:
    import pandas as pd
except ImportError:
    print("请先安装依赖: pip install pandas openpyxl")


# 工具参数定义
class ParseDataFileParams(BaseModel):
    """解析数据文件的参数"""
    file_path: str = Field(description="数据文件的完整路径或上传文件的URL（如 http://localhost:5000/files/xxx.xlsx）")
    preview_rows: int = Field(default=10, description="预览的行数，默认10行")
    include_statistics: bool = Field(default=True, description="是否包含统计信息，默认True")
    save_to_file: bool = Field(default=False, description="是否将结果保存到文件，默认False")
    output_path: str = Field(default="", description="输出文件路径，如果save_to_file为True则必填")


# 辅助函数
def _detect_file_type(file_path: str) -> str:
    """检测文件类型"""
    suffix = Path(file_path).suffix.lower()
    if suffix in ['.xlsx', '.xls']:
        return 'excel'
    elif suffix == '.csv':
        return 'csv'
    elif suffix == '.json':
        return 'json'
    else:
        raise ValueError(f"不支持的文件格式: {suffix}。支持的格式: .xlsx, .xls, .csv, .json")


def _parse_excel(file_path: str, preview_rows: int = 10) -> Dict:
    """解析Excel文件"""
    print(f"开始解析Excel文件: {file_path}")
    
    # 读取所有工作表
    excel_file = pd.ExcelFile(file_path)
    sheet_names = excel_file.sheet_names
    print(f"  发现 {len(sheet_names)} 个工作表: {', '.join(sheet_names)}")
    
    result = {
        'file_type': 'Excel',
        'total_sheets': len(sheet_names),
        'sheets': []
    }
    
    for sheet_name in sheet_names:
        print(f"\n  处理工作表: {sheet_name}")
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        sheet_data = {
            'sheet_name': sheet_name,
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': list(df.columns),
            'column_types': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'preview_data': df.head(preview_rows).to_dict('records'),
            'preview_text': df.head(preview_rows).to_string()
        }
        
        print(f"    行数: {len(df)}, 列数: {len(df.columns)}")
        
        result['sheets'].append(sheet_data)
    
    return result


def _parse_csv(file_path: str, preview_rows: int = 10) -> Dict:
    """解析CSV文件"""
    print(f"开始解析CSV文件: {file_path}")
    
    # 尝试自动检测分隔符
    try:
        # 先读取一小部分来检测
        df = pd.read_csv(file_path, nrows=5)
        separator = ','
    except:
        # 尝试其他常见分隔符
        for sep in ['\t', ';', '|']:
            try:
                df = pd.read_csv(file_path, sep=sep, nrows=5)
                separator = sep
                break
            except:
                continue
    
    # 读取完整文件
    df = pd.read_csv(file_path, sep=separator)
    
    print(f"  分隔符: {repr(separator)}")
    print(f"  行数: {len(df)}, 列数: {len(df.columns)}")
    
    result = {
        'file_type': 'CSV',
        'separator': separator,
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'columns': list(df.columns),
        'column_types': {col: str(dtype) for col, dtype in df.dtypes.items()},
        'preview_data': df.head(preview_rows).to_dict('records'),
        'preview_text': df.head(preview_rows).to_string()
    }
    
    return result


def _parse_json(file_path: str, preview_rows: int = 10) -> Dict:
    """解析JSON文件"""
    print(f"开始解析JSON文件: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    result = {
        'file_type': 'JSON',
        'data_type': type(data).__name__,
    }
    
    # 如果是列表，尝试转换为DataFrame
    if isinstance(data, list):
        if len(data) > 0 and isinstance(data[0], dict):
            # 列表中包含字典，类似表格数据
            df = pd.DataFrame(data)
            
            result.update({
                'structure': 'list_of_objects',
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'columns': list(df.columns),
                'column_types': {col: str(dtype) for col, dtype in df.dtypes.items()},
                'preview_data': df.head(preview_rows).to_dict('records'),
                'preview_text': df.head(preview_rows).to_string()
            })
            
            print(f"  结构: 对象列表")
            print(f"  行数: {len(df)}, 列数: {len(df.columns)}")
        else:
            # 简单列表
            result.update({
                'structure': 'simple_list',
                'total_items': len(data),
                'preview_data': data[:preview_rows],
                'preview_text': json.dumps(data[:preview_rows], ensure_ascii=False, indent=2)
            })
            
            print(f"  结构: 简单列表")
            print(f"  元素数: {len(data)}")
    
    elif isinstance(data, dict):
        # 字典结构
        # 尝试检测是否包含表格数据
        has_table = False
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                has_table = True
                break
        
        if has_table:
            result['structure'] = 'nested_object_with_tables'
            result['keys'] = list(data.keys())
            result['preview_text'] = json.dumps({k: v[:preview_rows] if isinstance(v, list) else v 
                                                 for k, v in list(data.items())[:5]}, 
                                                ensure_ascii=False, indent=2)
            print(f"  结构: 嵌套对象（包含表格数据）")
        else:
            result['structure'] = 'simple_object'
            result['keys'] = list(data.keys())
            result['preview_text'] = json.dumps(data, ensure_ascii=False, indent=2)[:1000]
            print(f"  结构: 简单对象")
    
    else:
        result.update({
            'structure': 'other',
            'preview_text': str(data)[:1000]
        })
    
    return result


def _calculate_statistics(result: Dict) -> Dict:
    """计算数据统计信息"""
    stats = {}
    
    if result['file_type'] == 'Excel':
        stats['total_sheets'] = result['total_sheets']
        stats['sheets_info'] = []
        
        for sheet in result['sheets']:
            sheet_stats = {
                'name': sheet['sheet_name'],
                'rows': sheet['total_rows'],
                'columns': sheet['total_columns'],
                'column_names': sheet['columns']
            }
            stats['sheets_info'].append(sheet_stats)
    
    elif result['file_type'] == 'CSV':
        stats['total_rows'] = result['total_rows']
        stats['total_columns'] = result['total_columns']
        stats['column_names'] = result['columns']
    
    elif result['file_type'] == 'JSON':
        stats['data_type'] = result['data_type']
        stats['structure'] = result['structure']
        
        if 'total_rows' in result:
            stats['total_rows'] = result['total_rows']
            stats['total_columns'] = result['total_columns']
            stats['column_names'] = result['columns']
        elif 'total_items' in result:
            stats['total_items'] = result['total_items']
        elif 'keys' in result:
            stats['keys'] = result['keys']
    
    return stats


def _format_result(result: Dict, include_statistics: bool = True) -> str:
    """格式化解析结果为可读文本"""
    lines = []
    
    lines.append(f"文件类型: {result['file_type']}")
    lines.append("")
    
    # 统计信息
    if include_statistics:
        lines.append("【统计信息】")
        stats = _calculate_statistics(result)
        
        if result['file_type'] == 'Excel':
            lines.append(f"  工作表数量: {stats['total_sheets']}")
            for sheet_info in stats['sheets_info']:
                lines.append(f"\n  工作表: {sheet_info['name']}")
                lines.append(f"    行数: {sheet_info['rows']}")
                lines.append(f"    列数: {sheet_info['columns']}")
                lines.append(f"    列名: {', '.join(sheet_info['column_names'])}")
        
        elif result['file_type'] == 'CSV':
            lines.append(f"  分隔符: {repr(result['separator'])}")
            lines.append(f"  行数: {stats['total_rows']}")
            lines.append(f"  列数: {stats['total_columns']}")
            lines.append(f"  列名: {', '.join(stats['column_names'])}")
        
        elif result['file_type'] == 'JSON':
            lines.append(f"  数据类型: {stats['data_type']}")
            lines.append(f"  结构: {stats['structure']}")
            
            if 'total_rows' in stats:
                lines.append(f"  行数: {stats['total_rows']}")
                lines.append(f"  列数: {stats['total_columns']}")
                lines.append(f"  列名: {', '.join(stats['column_names'])}")
            elif 'total_items' in stats:
                lines.append(f"  元素数: {stats['total_items']}")
            elif 'keys' in stats:
                lines.append(f"  键: {', '.join(stats['keys'])}")
        
        lines.append("")
    
    # 数据预览
    lines.append("【数据预览】")
    
    if result['file_type'] == 'Excel':
        for sheet in result['sheets']:
            lines.append(f"\n工作表: {sheet['sheet_name']}")
            lines.append(sheet['preview_text'])
    
    elif result['file_type'] in ['CSV', 'JSON']:
        if 'preview_text' in result:
            lines.append(result['preview_text'])
    
    return '\n'.join(lines)


def _parse_data_file_complete(file_path: str, preview_rows: int = 10) -> Dict:
    """
    完整解析数据文件（Excel/CSV/JSON）
    
    Args:
        file_path: 文件路径或URL
        preview_rows: 预览行数
    
    Returns:
        包含完整数据信息的字典
    """
    # 处理 URL 格式的路径
    if file_path.startswith('http://') or file_path.startswith('https://'):
        # 从 URL 中提取文件名
        parsed_url = urlparse(file_path)
        filename = os.path.basename(parsed_url.path)
        # 构建临时文件夹的完整路径
        local_file_path = os.path.join(tempfile.gettempdir(), filename)
        print(f"检测到URL格式，转换为本地路径: {local_file_path}")
    else:
        local_file_path = file_path
    
    if not Path(local_file_path).exists():
        raise FileNotFoundError(f"文件不存在: {local_file_path}")
    
    # 检测文件类型
    file_type = _detect_file_type(local_file_path)
    
    # 根据类型解析
    if file_type == 'excel':
        result = _parse_excel(local_file_path, preview_rows)
    elif file_type == 'csv':
        result = _parse_csv(local_file_path, preview_rows)
    elif file_type == 'json':
        result = _parse_json(local_file_path, preview_rows)
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")
    
    result['file_path'] = file_path
    result['file_name'] = Path(local_file_path).name
    result['file_size'] = Path(local_file_path).stat().st_size
    
    print(f"\n{'='*80}")
    print("文件解析完成！")
    print(f"{'='*80}")
    
    return result


def _save_result_to_file(result: Dict, output_path: str):
    """将解析结果保存到文件"""
    content = _format_result(result, include_statistics=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n结果已保存到: {output_path}")


# 定义langchain工具

@tool(args_schema=ParseDataFileParams)
def parse_data_file(
    file_path: str,
    preview_rows: int = 10,
    include_statistics: bool = True,
    save_to_file: bool = False,
    output_path: str = ""
) -> str:
    """
    完整解析数据文件（Excel/CSV/JSON），提取结构信息、统计数据并预览内容。
    
    适用场景:
    - 分析Excel表格数据和多个工作表
    - 解析CSV数据文件
    - 读取和理解JSON数据结构
    - 获取数据文件的基本统计信息
    - 预览数据内容和列信息
    - 检查数据文件的格式和结构
    - 统计数据行数、列数、数据类型
    
    功能特点:
    - 支持Excel文件（.xlsx, .xls）- 自动处理多个工作表
    - 支持CSV文件 - 自动检测分隔符（逗号、制表符、分号等）
    - 支持JSON文件 - 智能识别不同的JSON结构（对象列表、嵌套对象等）
    - 提取列名和数据类型信息
    - 统计行数、列数等基本信息
    - 数据预览（可配置预览行数）
    - 可选保存结果到文件
    - 支持本地路径和上传文件URL（自动从临时文件夹获取）
    
    参数说明:
    - file_path: 数据文件的完整路径或上传文件的URL（如 http://localhost:5000/files/xxx.xlsx）
    - preview_rows: 预览的行数，默认10行
    - include_statistics: 是否包含统计信息，默认True
    - save_to_file: 是否将结果保存到文件
    - output_path: 输出文件路径（当save_to_file为True时必填）
    
    注意事项:
    - 需要安装pandas和openpyxl库
    - Excel文件需要openpyxl支持
    - CSV文件会自动检测分隔符
    - JSON文件支持多种结构（列表、对象、嵌套结构等）
    - 大文件只预览指定行数以提高性能
    
    返回:
    - 包含数据文件完整信息的文本，包括统计信息和数据预览
    """
    try:
        # 解析文件
        result = _parse_data_file_complete(file_path, preview_rows)
        
        # 格式化结果
        formatted_result = _format_result(result, include_statistics)
        
        # 可选保存到文件
        if save_to_file:
            if not output_path:
                output_path = str(Path(file_path).with_suffix('.txt'))
            _save_result_to_file(result, output_path)
        
        # 构建摘要信息
        summary_parts = [f"""数据文件解析完成！

📄 文件信息:
  - 文件名: {result['file_name']}
  - 文件大小: {result['file_size']:,} 字节 ({result['file_size'] / 1024:.2f} KB)
  - 文件类型: {result['file_type']}
"""]
        
        # 添加类型特定的统计信息
        if result['file_type'] == 'Excel':
            summary_parts.append(f"  - 工作表数: {result['total_sheets']}")
            total_rows = sum(sheet['total_rows'] for sheet in result['sheets'])
            summary_parts.append(f"  - 总行数: {total_rows}")
        elif result['file_type'] == 'CSV':
            summary_parts.append(f"  - 行数: {result['total_rows']}")
            summary_parts.append(f"  - 列数: {result['total_columns']}")
        elif result['file_type'] == 'JSON':
            summary_parts.append(f"  - 数据结构: {result['structure']}")
            if 'total_rows' in result:
                summary_parts.append(f"  - 行数: {result['total_rows']}")
        
        summary_parts.append(f"""
{'='*80}
完整内容:
{'='*80}

{formatted_result}
""")
        
        return '\n'.join(summary_parts)
        
    except FileNotFoundError as e:
        return f"❌ 错误: {str(e)}"
    except Exception as e:
        return f"❌ 文件解析失败: {str(e)}\n请确保文件格式正确且已安装必要的依赖（pip install pandas openpyxl）"


# 导出工具列表
data_parser_tools = [
    parse_data_file
]
