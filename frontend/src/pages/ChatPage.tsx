import { Button, Card, Form, Input, List, Tag, Typography, message } from 'antd';
import { useState } from 'react';
import { api } from '../services/api';

interface ChatResult {
  conversation_id: number;
  message_id: number;
  answer: string;
  citations: Array<Record<string, any>>;
  retrieval_debug: Record<string, any>;
}

export function ChatPage() {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [result, setResult] = useState<ChatResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const onFinish = async (values: { question: string; task_id?: number }) => {
    setLoading(true);
    try {
      const { data } = await api.post<ChatResult>('/api/chat', {
        ...values,
        conversation_id: conversationId,
        filters: {},
      });
      setConversationId(data.conversation_id);
      setResult(data);
    } catch {
      messageApi.error('问答失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page narrow-page">
      {contextHolder}
      <Typography.Title level={3}>辅助问答</Typography.Title>
      <Card>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item name="task_id" label="关联任务 ID"><Input /></Form.Item>
          <Form.Item name="question" label="问题" rules={[{ required: true }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>提问</Button>
        </Form>
      </Card>
      {result && (
        <Card className="result-card" title="回答">
          <Typography.Paragraph style={{ whiteSpace: 'pre-wrap' }}>{result.answer}</Typography.Paragraph>
          <Typography.Title level={5}>引用来源</Typography.Title>
          <List
            dataSource={result.citations}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={<Tag>{item.citation_code}</Tag>}
                  description={item.quote}
                />
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  );
}
