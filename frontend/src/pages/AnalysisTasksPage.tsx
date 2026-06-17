import { Button, Card, Form, Input, InputNumber, Space, Table, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { AnalysisTask } from '../types/api';

export function AnalysisTasksPage() {
  const [tasks, setTasks] = useState<AnalysisTask[]>([]);
  const [selected, setSelected] = useState<AnalysisTask | null>(null);
  const [loading, setLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const fetchTasks = async () => {
    const { data } = await api.get<AnalysisTask[]>('/api/analysis-tasks');
    setTasks(data);
    if (selected) {
      const refreshed = data.find((item) => item.id === selected.id);
      if (refreshed) setSelected(refreshed);
    }
  };

  useEffect(() => { fetchTasks().catch(() => messageApi.error('任务列表加载失败')); }, []);

  const createTask = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const { data } = await api.post<AnalysisTask>('/api/analysis-tasks', values);
      setSelected(data);
      await fetchTasks();
    } catch {
      messageApi.error('创建任务失败');
    } finally {
      setLoading(false);
    }
  };

  const runTask = async (taskId: number) => {
    setLoading(true);
    try {
      const { data } = await api.post<AnalysisTask>(`/api/analysis-tasks/${taskId}/run`);
      setSelected(data);
      await fetchTasks();
    } catch (error: any) {
      messageApi.error(error.response?.data?.detail || '任务运行失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      {contextHolder}
      <Typography.Title level={3}>分析任务</Typography.Title>
      <Card>
        <Form layout="inline" onFinish={createTask}>
          <Form.Item name="product_name"><Input placeholder="产品名称" /></Form.Item>
          <Form.Item name="product_model"><Input placeholder="型号" /></Form.Item>
          <Form.Item name="product_id"><InputNumber placeholder="产品 ID" /></Form.Item>
          <Form.Item name="user_question"><Input placeholder="分析目标" /></Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>创建任务</Button>
        </Form>
      </Card>
      <Table
        rowKey="id"
        className="result-card"
        dataSource={tasks}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 80 },
          { title: '产品输入', dataIndex: 'product_name_input' },
          { title: '产品 ID', dataIndex: 'product_id', width: 100 },
          { title: '状态', dataIndex: 'status', width: 120, render: (value) => <Tag>{value}</Tag> },
          { title: '当前步骤', dataIndex: 'current_step', width: 160 },
          { title: '操作', width: 180, render: (_, record) => (
            <Space>
              <Button onClick={() => setSelected(record)}>查看</Button>
              <Button type="primary" onClick={() => runTask(record.id)} loading={loading}>运行</Button>
            </Space>
          ) },
        ]}
      />
      {selected && (
        <Card title={`任务 #${selected.id}`} className="result-card">
          <Table rowKey="id" dataSource={selected.steps} pagination={false} columns={[
            { title: '节点', dataIndex: 'step_name' },
            { title: '状态', dataIndex: 'status', render: (value) => <Tag>{value}</Tag> },
            { title: '错误', dataIndex: 'error_message' },
            { title: '输出', dataIndex: 'output_json', render: (value) => <pre className="json-preview">{JSON.stringify(value, null, 2)}</pre> },
          ]} />
        </Card>
      )}
    </div>
  );
}
