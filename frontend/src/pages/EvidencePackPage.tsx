import { Button, Card, Form, Input, InputNumber, Table, Tag, Typography, message } from 'antd';
import { useState } from 'react';
import { api } from '../services/api';
import type { EvidenceItem } from '../types/api';

interface EvidenceResponse {
  query: string;
  items: EvidenceItem[];
  missing_information: string[];
  debug: Record<string, unknown>;
}

export function EvidencePackPage() {
  const [result, setResult] = useState<EvidenceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const { data } = await api.post<EvidenceResponse>('/api/retrieval/evidence-pack', values);
      setResult(data);
    } catch {
      messageApi.error('证据包生成失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      {contextHolder}
      <Typography.Title level={3}>Evidence Pack</Typography.Title>
      <Card>
        <Form layout="inline" onFinish={onFinish} initialValues={{ top_k: 12 }}>
          <Form.Item name="query" rules={[{ required: true }]}><Input.TextArea rows={2} placeholder="检索问题或分析目标" /></Form.Item>
          <Form.Item name="product_id"><InputNumber placeholder="产品 ID" /></Form.Item>
          <Form.Item name="target_industry_id"><InputNumber placeholder="行业 ID" /></Form.Item>
          <Form.Item name="top_k"><InputNumber min={1} max={50} /></Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>生成</Button>
        </Form>
      </Card>
      {result && (
        <Card className="result-card" title="证据结果">
          {result.missing_information.map((item) => <Tag key={item} color="orange">{item}</Tag>)}
          <Table
            rowKey={(row) => `${row.citation_code}-${row.chunk_id}`}
            dataSource={result.items}
            columns={[
              { title: '引用', dataIndex: 'citation_code', width: 90 },
              { title: '分组', dataIndex: 'group_name', width: 150 },
              { title: '分数', dataIndex: 'score', width: 90 },
              { title: '可信', dataIndex: 'trust_level', width: 80 },
              { title: '内容', dataIndex: 'quote', ellipsis: true },
            ]}
          />
        </Card>
      )}
    </div>
  );
}
