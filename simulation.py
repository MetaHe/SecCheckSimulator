"""
仿真核心逻辑
"""
import simpy
import numpy as np
import pandas as pd
import collections

import config as cfg

class SpectatorStats:
    """用于记录单个观众在仿真过程中的各项时间指标"""
    def __init__(self, id, arrival_time, group_size, path_name):
        self.id = id
        self.group_size = group_size
        self.path_name = path_name
        self.arrival_time = arrival_time
        self.transport_delay = 0
        self.walk_duration = 0 # 理想步行时长
        self.walk_delay_congestion = 0 # 拥堵导致的步行延迟
        self.walk_delay_random = 0
        self.security_queue_wait_time = 0
        self.security_process_time = 0
        self.descend_queue_wait_time = 0
        self.descend_process_time = 0
        self.descend_method = ""  # 记录下行方式："escalator" 或 "stairs"
        self.finish_time = -1
        self.is_finished = False

    def total_time(self):
        return self.finish_time - self.arrival_time if self.is_finished else -1

    def to_dict(self):
        return {
            "ID": self.id,
            "群组规模": self.group_size,
            "入口路径": self.path_name,
            "到达公园时间": self.arrival_time,
            "交通延迟": self.transport_delay,
            "理想步行时长": self.walk_duration,
            "拥堵延迟": self.walk_delay_congestion,
            "随机扰动延迟": self.walk_delay_random,
            "安检排队时长": self.security_queue_wait_time,
            "安检处理时长": self.security_process_time,
            "下楼排队时长": self.descend_queue_wait_time,
            "下楼过程时长": self.descend_process_time,
            "下行方式": self.descend_method,
            "完成进站时间": self.finish_time,
            "是否在规定时间内完成": self.is_finished,
            "总耗时": self.total_time()
        }


class Simulation:
    """仿真主类"""
    def __init__(self):
        self.env = simpy.Environment()
        self.random_state = np.random.RandomState(cfg.RANDOM_SEED)
        
        # 定义资源
        self.security_lanes = [simpy.Resource(self.env, capacity=1) for _ in range(cfg.TOTAL_SECURITY_LANES)]
        self.north_lanes = self.security_lanes[:cfg.LANES_PER_TENT]
        self.south_lanes = self.security_lanes[cfg.LANES_PER_TENT:]
        
        self.escalator = simpy.Resource(self.env, capacity=cfg.ESCALATOR_PHYSICAL_CAPACITY)
        self.stairs = simpy.Resource(self.env, capacity=9999) # 楼梯视为无限容量

        # 定义路径状态
        self.paths = {
            name: {
                "length": details["length"],
                "width": details["width"],
                "area": details["length"] * details["width"],
                "population": 0,
            }
            for name, details in cfg.PATHS.items()
        }

        # 统计数据
        self.spectator_stats = []
        self.system_state_log = []

    def get_transport_delay(self):
        """模块1: 计算交通延迟"""
        mode = self.random_state.choice(
            list(cfg.TRANSPORT_PROBS.keys()), 
            p=list(cfg.TRANSPORT_PROBS.values())
        )
        delay = 0
        if mode == "自驾":
            delay = self.random_state.normal(cfg.DRIVE_DELAY_MEAN_S, cfg.DRIVE_DELAY_STD_S)
        elif mode == "公交":
            delay = self.random_state.uniform(cfg.BUS_DELAY_MIN_S, cfg.BUS_DELAY_MAX_S)
        
        return max(0, delay)

    def assign_path(self):
        """模块2: 为一个组分配路径"""
        path_names = list(cfg.PATH_CHOICE_PROBS.keys())
        probs = list(cfg.PATH_CHOICE_PROBS.values())
        return self.random_state.choice(path_names, p=probs)

    def get_walking_speed(self, path_name):
        """模块2: 根据路径拥挤程度计算动态步行速度"""
        path = self.paths[path_name]
        if path["area"] == 0:
            return cfg.BASE_WALKING_SPEED_MPS

        density = path["population"] / path["area"]
        
        speed = cfg.BASE_WALKING_SPEED_MPS
        if density > cfg.CONGESTION_DENSITY_THRESHOLD:
            density_over_threshold = density - cfg.CONGESTION_DENSITY_THRESHOLD
            reduction_steps = density_over_threshold / cfg.CONGESTION_SPEED_REDUCTION_UNIT_DENSITY
            speed_reduction = reduction_steps * cfg.CONGESTION_SPEED_REDUCTION_FACTOR
            speed *= (1 - speed_reduction)

        return max(speed, cfg.MIN_WALKING_SPEED_MPS)

    def spectator_process(self, spectator_id, group_size, path_name):
        """单个观众的完整仿真流程"""
        stats = SpectatorStats(spectator_id, self.env.now, group_size, path_name)
        self.spectator_stats.append(stats)

        # 1. 交通延迟
        stats.transport_delay = self.get_transport_delay()
        yield self.env.timeout(stats.transport_delay)

        # 2. 公园内步行 (含拥挤模型)
        path_details = self.paths[path_name]
        path_length = path_details["length"]
        
        # 2.1 更新路径实时人数
        path_details["population"] += 1

        # 2.2 计算步行速度和时间
        current_walking_speed = self.get_walking_speed(path_name)
        ideal_walk_duration = path_length / cfg.BASE_WALKING_SPEED_MPS
        actual_walk_duration = path_length / current_walking_speed
        
        stats.walk_duration = ideal_walk_duration
        stats.walk_delay_congestion = actual_walk_duration - ideal_walk_duration
        stats.walk_delay_random = self.random_state.uniform(cfg.PATH_DISTURBANCE_MIN_S, cfg.PATH_DISTURBANCE_MAX_S)
        
        yield self.env.timeout(actual_walk_duration)
        yield self.env.timeout(stats.walk_delay_random)

        # 2.3 离开路径，更新人数
        path_details["population"] -= 1

        # 3. 安检过程
        security_queue_start_time = self.env.now
        
        # 3.1 大棚选择 (选择总排队人数较少的大棚)
        north_queue = sum(len(res.queue) for res in self.north_lanes)
        south_queue = sum(len(res.queue) for res in self.south_lanes)
        chosen_tent_lanes = self.north_lanes if north_queue <= south_queue else self.south_lanes
        
        # 3.2 通道选择 (选择该大棚内排队人数最少的通道)
        chosen_lane = min(chosen_tent_lanes, key=lambda r: len(r.queue))

        with chosen_lane.request() as request:
            yield request
            stats.security_queue_wait_time = self.env.now - security_queue_start_time
            
            # 3.3 安检处理 (含群组延迟)
            security_process_start_time = self.env.now
            
            delay_factor = cfg.GROUP_COORDINATION_DELAY_FACTOR if group_size > 1 else 1.0

            # 模拟安检失败重试
            while self.random_state.rand() < cfg.SECURITY_FAILURE_RATE:
                process_time = self.random_state.exponential(cfg.SECURITY_CHECK_TIME_MEAN_S)
                yield self.env.timeout(process_time * delay_factor)

            # 正常安检
            process_time = self.random_state.exponential(cfg.SECURITY_CHECK_TIME_MEAN_S)
            yield self.env.timeout(process_time * delay_factor)
            
            stats.security_process_time = self.env.now - security_process_start_time

            # 模拟通道故障
            if self.random_state.rand() < cfg.LANE_FAILURE_PROB_PER_PERSON:
                failure_duration = self.random_state.uniform(
                    cfg.LANE_FAILURE_DURATION_MIN_S,
                    cfg.LANE_FAILURE_DURATION_MAX_S
                )
                yield self.env.timeout(failure_duration)

        # 4. 下行方式选择
        descend_queue_start_time = self.env.now
        
        use_escalator_prob = cfg.DESCEND_INITIAL_PROBS['escalator']
        if len(self.escalator.queue) > cfg.ESCALATOR_QUEUE_THRESHOLD_FOR_ADJUST:
            use_escalator_prob = cfg.DESCEND_ADJUSTED_PROBS['escalator']

        # 4.1 走扶梯
        if self.random_state.rand() < use_escalator_prob:
            stats.descend_method = "escalator"
            with self.escalator.request() as request:
                yield request
                stats.descend_queue_wait_time = self.env.now - descend_queue_start_time
                descend_process_start_time = self.env.now
                yield self.env.timeout(1 / cfg.ESCALATOR_CAPACITY_PER_SEC)
                stats.descend_process_time = self.env.now - descend_process_start_time
        # 4.2 走楼梯
        else:
            stats.descend_method = "stairs"
            with self.stairs.request() as request:
                yield request
                stats.descend_queue_wait_time = self.env.now - descend_queue_start_time
                descend_process_start_time = self.env.now
                yield self.env.timeout(cfg.STAIRS_PERSON_CROSS_TIME_S)
                stats.descend_process_time = self.env.now - descend_process_start_time

        # 5. 完成进站
        stats.finish_time = self.env.now
        stats.is_finished = True

        if spectator_id % cfg.SPECTATOR_LOG_INTERVAL == 0:
            print(f"观众 {spectator_id} 在 {self.env.now:.2f} 秒完成进站。")

    def setup(self):
        """设置观众生成器"""
        self.env.process(self.monitor())

        spectator_id_counter = 0
        group_sizes_list = list(cfg.GROUP_SIZE_PROBS.keys())
        group_probs_list = list(cfg.GROUP_SIZE_PROBS.values())

        while spectator_id_counter < cfg.TOTAL_SPECTATORS:
            # 确定组的大小
            group_size = self.random_state.choice(group_sizes_list, p=group_probs_list)
            group_size = min(group_size, cfg.TOTAL_SPECTATORS - spectator_id_counter)
            
            # 随机生成该组的到达时间
            arrival_time = self.random_state.uniform(0, cfg.SIMULATION_DURATION_SECONDS)
            
            # 为该组分配路径
            path_name = self.assign_path()

            # 启动一个"群组到达"进程
            self.env.process(self.group_arrival(
                start_id=spectator_id_counter,
                arrival_time=arrival_time,
                group_size=group_size,
                path_name=path_name
            ))
            
            spectator_id_counter += group_size

    def group_arrival(self, start_id, arrival_time, group_size, path_name):
        """一个群组的到达事件"""
        yield self.env.timeout(arrival_time)
        # 群组成员同时开始行动
        for i in range(group_size):
            spectator_id = start_id + i
            self.env.process(self.spectator_process(spectator_id, group_size, path_name))

    def monitor(self):
        """定期记录系统状态"""
        while True:
            state = {
                "时间(s)": self.env.now,
                "北侧安检队列总人数": sum(len(r.queue) for r in self.north_lanes),
                "南侧安检队列总人数": sum(len(r.queue) for r in self.south_lanes),
                "北侧安检区使用中通道数": sum(r.count for r in self.north_lanes),
                "南侧安检区使用中通道数": sum(r.count for r in self.south_lanes),
                "电梯队列人数": len(self.escalator.queue),
                "电梯使用中人数": self.escalator.count,
                "楼梯使用中人数": self.stairs.count,
                "楼梯密度(人/米)": self.stairs.count / cfg.STAIRS_WIDTH_M if cfg.STAIRS_WIDTH_M > 0 else 0
            }
            # 记录各路径的实时状态
            for name, details in self.paths.items():
                state[f"{name} 人数"] = details["population"]
                state[f"{name} 密度(人/m^2)"] = details["population"] / details["area"] if details["area"] > 0 else 0
            
            self.system_state_log.append(state)
            yield self.env.timeout(cfg.MONITOR_INTERVAL_S)

    def run(self):
        """运行仿真"""
        print("仿真开始...")
        self.setup()
        self.env.run(until=cfg.SIMULATION_DURATION_SECONDS)
        print("仿真结束。")

    def get_results(self):
        """将统计数据转换为DataFrame"""
        spectator_df = pd.DataFrame([s.to_dict() for s in self.spectator_stats])
        system_df = pd.DataFrame(self.system_state_log)
        return spectator_df, system_df 