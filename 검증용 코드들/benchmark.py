#!/usr/bin/env python3
"""list vs heap 매칭 성능 벤치마크 (재현용)."""
import heapq
import statistics
import time

from orderbook import OrderBook, SIDE_BUY, SIDE_SELL

SIZES = [100, 500, 1000, 2000, 5000]
M = 200  # 측정용 주문 수


def bench_list(n):
    ob = OrderBook()
    for i in range(n):
        ob.submit_order(SIDE_SELL, 100000 + i, 1)
    t0 = time.perf_counter()
    for _ in range(M):
        ob.submit_order(SIDE_BUY, 1, 1)
    return (time.perf_counter() - t0) / M * 1e6


class _HeapBook:
    def __init__(self):
        self.asks, self.bids, self.seq = [], [], 0

    def submit(self, side, price):
        self.seq += 1
        if side == SIDE_BUY:
            if self.asks and self.asks[0][0] <= price:
                heapq.heappop(self.asks)
            else:
                heapq.heappush(self.bids, (-price, self.seq))
        else:
            heapq.heappush(self.asks, (price, self.seq))


def bench_heap(n):
    hb = _HeapBook()
    for i in range(n):
        hb.submit(SIDE_SELL, 100000 + i)
    t0 = time.perf_counter()
    for _ in range(M):
        hb.submit(SIDE_BUY, 1)
    return (time.perf_counter() - t0) / M * 1e6


def main():
    list_us, heap_us = [], []
    print(f"{'N':>6} {'list(µs/주문)':>16} {'heap(µs/주문)':>16}")
    for n in SIZES:
        l = statistics.median([bench_list(n) for _ in range(5)])
        h = statistics.median([bench_heap(n) for _ in range(5)])
        list_us.append(round(l, 2)); heap_us.append(round(h, 2))
        print(f"{n:>6} {l:>16.2f} {h:>16.2f}")

    i = SIZES.index(1000)
    print(f"\n[NFR-P-01] N=1000일 때 list {list_us[i]}µs = {list_us[i]/1000:.3f}ms "
          f"(기준 100ms 대비 {100/(list_us[i]/1000):.0f}배 여유)")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
        for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"]:
            try:
                font_manager.fontManager.addfont(p)
                plt.rcParams["font.family"] = font_manager.FontProperties(fname=p).get_name()
            except Exception:
                pass
        plt.rcParams["axes.unicode_minus"] = False
        fig, ax = plt.subplots(figsize=(8.5, 5))
        ax.plot(SIZES, list_us, "o-", color="#C0392B", lw=2, label="list (current)")
        ax.plot(SIZES, heap_us, "s-", color="#2E86C1", lw=2, label="heap (alt)")
        ax.set_yscale("log"); ax.grid(True, which="both", alpha=0.3)
        ax.set_xlabel("order book size N"); ax.set_ylabel("us per order (log)")
        ax.set_title("list vs heap per-order time")
        ax.legend()
        import os
        os.makedirs("reports", exist_ok=True)
        plt.tight_layout(); plt.savefig("reports/benchmark_list_vs_heap.png", dpi=150)
        print("\nsaved reports/benchmark_list_vs_heap.png")
    except ImportError:
        print("\n(matplotlib 없으면 차트는 건너뜀 - 콘솔 수치는 위에 있음)")


if __name__ == "__main__":
    main()
