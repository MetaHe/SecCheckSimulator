"""
仿真程序主入口
"""
import pandas as pd
import os
import numpy as np

from simulation import Simulation
import config as cfg

def create_summary(spectator_df, system_df):
    """根据观众数据和系统监控数据计算并生成汇总指标"""
    
    # ============================================================================
    # 1. 效率指标
    # ============================================================================
    # 总完成率：210分钟内完成进站人数比例
    finished_spectators = spectator_df[spectator_df['是否在规定时间内完成']]
    total_finished = len(finished_spectators)
    completion_rate = total_finished / cfg.TOTAL_SPECTATORS if cfg.TOTAL_SPECTATORS > 0 else 0
    
    # 平均进站时间：从到达公园到进入站台的平均耗时
    if total_finished > 0:
        avg_total_time_min = finished_spectators['总耗时'].mean() / 60
    else:
        avg_total_time_min = 0

    # ============================================================================
    # 2. 排队指标
    # ============================================================================
    # 最大队列长度：南/北大棚安检队列峰值
    north_max_queue = system_df['北侧安检队列总人数'].max() if not system_df.empty else 0
    south_max_queue = system_df['南侧安检队列总人数'].max() if not system_df.empty else 0
    
    # 电梯最大排队人数
    elevator_max_queue = system_df['电梯队列人数'].max() if not system_df.empty else 0
    
    # 平均队列长度：各关键节点统计
    north_avg_queue = system_df['北侧安检队列总人数'].mean() if not system_df.empty else 0
    south_avg_queue = system_df['南侧安检队列总人数'].mean() if not system_df.empty else 0
    elevator_avg_queue = system_df['电梯队列人数'].mean() if not system_df.empty else 0

    # ============================================================================
    # 3. 资源利用率
    # ============================================================================
    # 安检通道平均利用率（忙时占比）
    if not system_df.empty:
        north_utilization = (system_df['北侧安检区使用中通道数'].mean() / cfg.LANES_PER_TENT) * 100
        south_utilization = (system_df['南侧安检区使用中通道数'].mean() / cfg.LANES_PER_TENT) * 100
        overall_utilization = ((system_df['北侧安检区使用中通道数'] + system_df['南侧安检区使用中通道数']).mean() / cfg.TOTAL_SECURITY_LANES) * 100
        
        # 电梯利用率
        elevator_utilization = (system_df['电梯使用中人数'].mean() / cfg.ESCALATOR_PHYSICAL_CAPACITY) * 100
    else:
        north_utilization = south_utilization = overall_utilization = elevator_utilization = 0

    # ============================================================================
    # 4. 瓶颈分析 - 各环节延误时间分布
    # ============================================================================
    if total_finished > 0:
        # 平均各环节耗时
        avg_transport_delay = finished_spectators['交通延迟'].mean() / 60  # 分钟
        avg_walk_time = finished_spectators['步行时长'].mean() / 60
        avg_security_queue = finished_spectators['安检排队时长'].mean() / 60
        avg_security_process = finished_spectators['安检处理时长'].mean() / 60
        avg_descend_queue = finished_spectators['下楼排队时长'].mean() / 60
        avg_descend_process = finished_spectators['下楼过程时长'].mean() / 60
        
        # 各环节时间分布的标准差（体现波动性）
        std_security_queue = finished_spectators['安检排队时长'].std() / 60
        std_descend_queue = finished_spectators['下楼排队时长'].std() / 60
    else:
        avg_transport_delay = avg_walk_time = avg_security_queue = avg_security_process = 0
        avg_descend_queue = avg_descend_process = std_security_queue = std_descend_queue = 0

    # ============================================================================
    # 创建汇总报告
    # ============================================================================
    summary_sections = []
    
    # 效率指标
    efficiency_data = {
        "指标类别": ["效率指标"] * 2,
        "指标名称": [
            "总完成率 (%)",
            "平均进站时间 (分钟)"
        ],
        "数值": [
            f"{completion_rate:.2%}",
            f"{avg_total_time_min:.2f}"
        ]
    }
    
    # 排队指标
    queue_data = {
        "指标类别": ["排队指标"] * 6,
        "指标名称": [
            "北侧安检最大队列长度 (人)",
            "南侧安检最大队列长度 (人)",
            "电梯最大排队人数 (人)",
            "北侧安检平均队列长度 (人)",
            "南侧安检平均队列长度 (人)",
            "电梯平均排队人数 (人)"
        ],
        "数值": [
            f"{north_max_queue:.0f}",
            f"{south_max_queue:.0f}",
            f"{elevator_max_queue:.0f}",
            f"{north_avg_queue:.1f}",
            f"{south_avg_queue:.1f}",
            f"{elevator_avg_queue:.1f}"
        ]
    }
    
    # 资源利用率
    utilization_data = {
        "指标类别": ["资源利用率"] * 4,
        "指标名称": [
            "整体安检通道利用率 (%)",
            "北侧安检通道利用率 (%)",
            "南侧安检通道利用率 (%)",
            "电梯利用率 (%)"
        ],
        "数值": [
            f"{overall_utilization:.1f}%",
            f"{north_utilization:.1f}%",
            f"{south_utilization:.1f}%",
            f"{elevator_utilization:.1f}%"
        ]
    }
    
    # ============================================================================
    # 5. 关键节点热力图数据 - 楼梯密度分析
    # ============================================================================
    if not system_df.empty:
        max_stairs_density = system_df['楼梯密度(人/米)'].max()
        avg_stairs_density = system_df['楼梯密度(人/米)'].mean()
        max_stairs_usage = system_df['楼梯使用中人数'].max()
        avg_stairs_usage = system_df['楼梯使用中人数'].mean()
    else:
        max_stairs_density = avg_stairs_density = max_stairs_usage = avg_stairs_usage = 0

    # ============================================================================
    # 6. 下行方式选择分析
    # ============================================================================
    if total_finished > 0:
        escalator_users = len(finished_spectators[finished_spectators['下行方式'] == 'escalator'])
        stairs_users = len(finished_spectators[finished_spectators['下行方式'] == 'stairs'])
        escalator_rate = escalator_users / total_finished * 100
        stairs_rate = stairs_users / total_finished * 100
    else:
        escalator_users = stairs_users = escalator_rate = stairs_rate = 0

    # 瓶颈分析
    bottleneck_data = {
        "指标类别": ["瓶颈分析"] * 16,
        "指标名称": [
            "交通延迟平均时间 (分钟)",
            "园内步行平均时间 (分钟)",
            "安检排队平均时间 (分钟)",
            "安检处理平均时间 (分钟)",
            "下楼排队平均时间 (分钟)",
            "下楼过程平均时间 (分钟)",
            "安检排队时间波动性 (标准差分钟)",
            "下楼排队时间波动性 (标准差分钟)",
            "楼梯最大密度 (人/米)",
            "楼梯平均密度 (人/米)",
            "楼梯最大使用人数 (人)",
            "楼梯平均使用人数 (人)",
            "选择电梯人数",
            "选择楼梯人数",
            "电梯选择率 (%)",
            "楼梯选择率 (%)"
        ],
        "数值": [
            f"{avg_transport_delay:.2f}",
            f"{avg_walk_time:.2f}",
            f"{avg_security_queue:.2f}",
            f"{avg_security_process:.2f}",
            f"{avg_descend_queue:.2f}",
            f"{avg_descend_process:.2f}",
            f"{std_security_queue:.2f}",
            f"{std_descend_queue:.2f}",
            f"{max_stairs_density:.1f}",
            f"{avg_stairs_density:.1f}",
            f"{max_stairs_usage:.0f}",
            f"{avg_stairs_usage:.1f}",
            f"{escalator_users}",
            f"{stairs_users}",
            f"{escalator_rate:.1f}%",
            f"{stairs_rate:.1f}%"
        ]
    }
    
    # 合并所有数据
    all_data = {
        "指标类别": (efficiency_data["指标类别"] + queue_data["指标类别"] + 
                     utilization_data["指标类别"] + bottleneck_data["指标类别"]),
        "指标名称": (efficiency_data["指标名称"] + queue_data["指标名称"] + 
                     utilization_data["指标名称"] + bottleneck_data["指标名称"]),
        "数值": (efficiency_data["数值"] + queue_data["数值"] + 
                 utilization_data["数值"] + bottleneck_data["数值"])
    }
    
    return pd.DataFrame(all_data)


def main():
    """主函数"""
    # 1. 初始化并运行仿真
    sim = Simulation()
    sim.run()

    # 2. 获取结果
    spectator_df, system_df = sim.get_results()

    # 确保输出目录存在
    os.makedirs(os.path.dirname(cfg.OUTPUT_FILE_NAME), exist_ok=True)

    # 3. 创建汇总报告
    summary_df = create_summary(spectator_df, system_df)
    
    # 4. 将所有数据写入一个Excel文件，每个DataFrame在一个单独的sheet中
    with pd.ExcelWriter(cfg.OUTPUT_FILE_NAME, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name='仿真结果汇总', index=False)
        spectator_df.to_excel(writer, sheet_name='所有观众详细数据', index=False)
        system_df.to_excel(writer, sheet_name='系统状态监控', index=False)

    print(f"仿真完成，结果已保存至 '{cfg.OUTPUT_FILE_NAME}'")
    print("\n仿真结果汇总:")
    
    # 设置pandas显示选项，避免重复打印
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main() 