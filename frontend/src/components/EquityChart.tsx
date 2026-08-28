'use client';

import React, { useEffect, useRef } from 'react';
import { Chart, registerables } from 'chart.js';
import { Play } from 'lucide-react';

Chart.register(...registerables);

interface EquityChartProps {
  equityData: number[];
  onRunBacktest: () => void;
}

export const EquityChart: React.FC<EquityChartProps> = ({ equityData, onRunBacktest }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    const ctx = canvasRef.current.getContext('2d');
    if (!ctx) return;

    if (chartRef.current) {
      chartRef.current.destroy();
    }

    const dataPoints = equityData && equityData.length > 0 ? equityData : [100000, 100250, 100180, 100450, 100800];

    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: dataPoints.map((_, i) => `Step ${i + 1}`),
        datasets: [
          {
            label: 'Portfolio Equity ($)',
            data: dataPoints,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false }, ticks: { color: '#6b7280', font: { size: 10 } } },
          y: { grid: { color: '#1f2937' }, ticks: { color: '#6b7280', font: { size: 10 } } },
        },
        plugins: { legend: { display: false } },
      },
    });

    return () => {
      if (chartRef.current) chartRef.current.destroy();
    };
  }, [equityData]);

  return (
    <div className="bg-darkcard border border-darkborder p-4 md:p-6 rounded-2xl shadow-xl space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base md:text-lg font-bold text-white flex items-center">
          <span className="w-2 h-2 rounded-full bg-blue-500 mr-2"></span> Strategy Equity Curve
        </h2>
        <button
          onClick={onRunBacktest}
          className="bg-gray-800 hover:bg-gray-700 active:scale-95 text-xs text-gray-200 px-3 py-1.5 rounded-lg border border-gray-700 transition flex items-center"
        >
          <Play className="w-3 h-3 mr-1 text-blue-400" /> Run Forex Backtest
        </button>
      </div>

      <div className="h-56 md:h-64 relative">
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
};
