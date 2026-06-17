import { Button, Card, Form, Input, List, Switch, Tag, Typography, message } from 'antd';
import { useState } from 'react';
import { api } from '../services/api';
import type { Product } from '../types/api';

interface IdentifyResponse {
  matched_product?: Product | null;
  candidates: Array<{ product: Product; confidence: number; match_type: string }>;
  missing_information: string[];
}

export function ProductIdentifyPage() {
  const [result, setResult] = useState<IdentifyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const onFinish = async (values: { query: string; product_name?: string; product_model?: string; create_if_missing?: boolean }) => {
    setLoading(true);
    try {
      const { data } = await api.post<IdentifyResponse>('/api/products/identify', values);
      setResult(data);
    } catch {
      messageApi.error('产品识别失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page narrow-page">
      {contextHolder}
      <Typography.Title level={3}>产品识别</Typography.Title>
      <Card>
        <Form layout="vertical" onFinish={onFinish} initialValues={{ create_if_missing: true }}>
          <Form.Item name="query" label="输入产品名称、型号或自然语言" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="product_name" label="产品名称"><Input /></Form.Item>
          <Form.Item name="product_model" label="产品型号"><Input /></Form.Item>
          <Form.Item name="create_if_missing" label="未命中时创建临时产品" valuePropName="checked"><Switch /></Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>识别</Button>
        </Form>
      </Card>
      {result && (
        <Card className="result-card" title="识别结果">
          {result.matched_product ? (
            <Typography.Paragraph>
              命中：<Tag color="green">{result.matched_product.name}</Tag>
              {result.matched_product.model}
            </Typography.Paragraph>
          ) : <Typography.Text type="secondary">未命中高置信度产品</Typography.Text>}
          <List
            dataSource={result.candidates}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={`${item.product.name}${item.product.model ? ` / ${item.product.model}` : ''}`}
                  description={`置信度 ${item.confidence} · ${item.match_type}`}
                />
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  );
}
