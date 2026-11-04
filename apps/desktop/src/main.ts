import { desktopApi } from './api';
import { DesktopApp } from './app';
import './styles.css';
import { appIconUrl } from './icon';

const favicon = document.createElement('link');
favicon.rel = 'icon';
favicon.href = appIconUrl;
document.head.append(favicon);

const root = document.querySelector<HTMLElement>('#app');
if (root) {
  const app = new DesktopApp(root, desktopApi);
  void app.start();
}
