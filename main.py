"""
仿真程序主入口
"""
import pandas as pd
import os

from simulation import Simulation
import config as cfg

def create_summary(spectator_df):
    """根据观众数据计算并生成汇总指标"""
    
    finished_spectators = spectator_df[spectator_df['是否在规定时间内完成']]
    
    total_finished = len(finished_spectators)
    completion_rate = total_finished / cfg.TOTAL_SPECTATORS if cfg.TOTAL_SPECTATORS > 0 else 0
    
    if total_finished > 0:
        avg_total_time_s = finished_spectators['总耗时'].mean()
        avg_security_queue_wait_s = finished_spectators['安检排队时长'].mean()
        avg_descend_queue_wait_s = finished_spectators['下楼排队时长'].mean()
    else:
        avg_total_time_s = 0
        avg_security_queue_wait_s = 0
        avg_descend_queue_wait_s = 0

    summary_data = {
        "指标": [
            "总完成率 (%)",
            "规定时间内完成总人数",
            "平均总耗时 (分钟)",
            "平均安检排队等候时间 (分钟)",
            "平均下楼排队等候时间 (分钟)"
        ],
        "数值": [
            f"{completion_rate:.2%}",
            total_finished,
            f"{avg_total_time_s / 60:.2f}",
            f"{avg_security_queue_wait_s / 60:.2f}",
            f"{avg_descend_queue_wait_s / 60:.2f}"
        ]
    }
    
    return pd.DataFrame(summary_data)


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
    summary_df = create_summary(spectator_df)
    
    # 4. 将所有数据写入一个Excel文件，每个DataFrame在一个单独的sheet中
    with pd.ExcelWriter(cfg.OUTPUT_FILE_NAME, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name='仿真结果汇总', index=False)
        spectator_df.to_excel(writer, sheet_name='所有观众详细数据', index=False)
        system_df.to_excel(writer, sheet_name='系统状态监控', index=False)

    print(f"仿真完成，结果已保存至 '{cfg.OUTPUT_FILE_NAME}'")
    print("\n仿真结果汇总:")
    print(summary_df)


if __name__ == "__main__":
    main() 