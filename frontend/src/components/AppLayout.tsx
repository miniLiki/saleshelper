import {
  AppstoreOutlined,
  BulbOutlined,
  CommentOutlined,
  DatabaseOutlined,
  FileAddOutlined,
  FileTextOutlined,
  LogoutOutlined,
  NodeIndexOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { Button, Layout, Menu, Space, Typography } from 'antd';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { clearSession, getStoredUser } from '../services/auth';

const { Header, Sider, Content } = Layout;

export function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = getStoredUser();

  const logout = () => {
    clearSession();
    navigate('/login');
  };

  return (
    <Layout className="app-shell">
      <Sider width={232} className="app-sider">
        <div className="brand" onClick={() => navigate('/documents')}>SalesHelper</div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          onClick={({ key }) => navigate(key)}
          items={[
            { key: '/documents', icon: <FileTextOutlined />, label: '资料管理' },
            { key: '/documents/upload', icon: <FileAddOutlined />, label: '上传资料' },
            { key: '/products/identify', icon: <BulbOutlined />, label: '产品识别' },
            { key: '/evidence-pack', icon: <DatabaseOutlined />, label: 'Evidence Pack' },
            { key: '/analysis-tasks', icon: <NodeIndexOutlined />, label: '分析任务' },
            { key: '/chat', icon: <CommentOutlined />, label: '辅助问答' },
            { key: '/admin', icon: <SettingOutlined />, label: '管理后台' },
          ]}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Space>
            <AppstoreOutlined />
            <Typography.Text strong>AI 产品分析推荐系统</Typography.Text>
          </Space>
          <Space>
            <Typography.Text>{user?.display_name || user?.username}</Typography.Text>
            <Button icon={<LogoutOutlined />} onClick={logout}>退出</Button>
          </Space>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
