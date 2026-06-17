import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { Button, Card, Form, Input, Typography, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { saveSession } from '../services/auth';
import type { LoginResponse } from '../types/api';

export function LoginPage() {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();

  const onFinish = async (values: { username: string; password: string }) => {
    try {
      const { data } = await api.post<LoginResponse>('/api/auth/login', values);
      saveSession(data);
      navigate('/documents');
    } catch {
      messageApi.error('用户名或密码错误');
    }
  };

  return (
    <div className="login-page">
      {contextHolder}
      <Card className="login-card">
        <Typography.Title level={2}>SalesHelper</Typography.Title>
        <Typography.Paragraph type="secondary">内部产品分析与销售辅助工作台</Typography.Paragraph>
        <Form layout="vertical" onFinish={onFinish} initialValues={{ username: 'admin' }}>
          <Form.Item name="username" label="账号" rules={[{ required: true, message: '请输入账号' }]}>
            <Input prefix={<UserOutlined />} autoComplete="username" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>登录</Button>
        </Form>
      </Card>
    </div>
  );
}
