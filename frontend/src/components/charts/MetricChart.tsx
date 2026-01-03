import React from 'react';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    TooltipProps
} from 'recharts';
import { Box, Typography, Paper, useTheme } from '@mui/material';

interface DataPoint {
    timestamp: number;
    value: number;
}

interface MetricChartProps {
    title: string;
    data: DataPoint[];
    color: string;
    unit: string;
    loading?: boolean;
    height?: number;
}

const CustomTooltip = ({ active, payload, label, unit }: any) => {
    if (active && payload && payload.length) {
        return (
            <Paper sx={{ p: 1, backgroundColor: '#1e1e1e', border: '1px solid #333' }}>
                <Typography variant="caption" sx={{ color: '#ccc' }}>
                    {new Date(Number(label) * 1000).toLocaleTimeString()}
                </Typography>
                <Typography variant="body2" sx={{ color: '#fff', fontWeight: 'bold' }}>
                    {payload[0].value?.toFixed(1)}{unit}
                </Typography>
            </Paper>
        );
    }
    return null;
};

const MetricChart: React.FC<MetricChartProps> = ({ title, data, color, unit, loading, height = 200 }) => {
    const theme = useTheme();

    if (loading) {
        return (
            <Box sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#252526', border: '1px solid #2d2d30', borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary">Loading...</Typography>
            </Box>
        );
    }

    if (!data || data.length === 0) {
        return (
            <Box sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#252526', border: '1px solid #2d2d30', borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary">No data available</Typography>
            </Box>
        );
    }

    return (
        <Box sx={{ bgcolor: '#252526', p: 2, borderRadius: 1, border: '1px solid #2d2d30' }}>
            <Typography variant="subtitle2" sx={{ color: '#ccc', mb: 2 }}>
                {title}
            </Typography>
            <Box sx={{ height: height - 40, width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data}>
                        <defs>
                            <linearGradient id={`color-${title}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                                <stop offset="95%" stopColor={color} stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                        <XAxis
                            dataKey="timestamp"
                            tickFormatter={(ts) => new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            stroke="#666"
                            tick={{ fontSize: 10 }}
                            minTickGap={30}
                        />
                        <YAxis
                            stroke="#666"
                            tick={{ fontSize: 10 }}
                            tickFormatter={(val) => `${val.toFixed(0)}${unit}`}
                        />
                        <Tooltip content={(props: any) => <CustomTooltip {...props} unit={unit} />} />
                        <Area
                            type="monotone"
                            dataKey="value"
                            stroke={color}
                            fillOpacity={1}
                            fill={`url(#color-${title})`}
                            isAnimationActive={false}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </Box>
        </Box>
    );
};

export default MetricChart;
