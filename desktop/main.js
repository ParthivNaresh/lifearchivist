const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const path = require('path');
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    titleBarStyle: 'hiddenInset',
    show: false
  });

  const startUrl = isDev 
    ? 'http://localhost:3000' 
    : `file://${path.join(__dirname, '../build/index.html')}`;
    
  console.log('NODE_ENV:', process.env.NODE_ENV);
  console.log('isDev:', isDev);
  console.log('Loading URL:', startUrl);
    
  mainWindow.loadURL(startUrl);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC handlers
ipcMain.handle('select-files', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile', 'multiSelections'],
    filters: [
      { name: 'All Supported Files', extensions: ['pdf', 'doc', 'docx', 'txt', 'md', 'rtf', 'xlsx', 'xls', 'csv', 'tsv', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'svg', 'mp3', 'wav', 'ogg', 'm4a', 'mp4', 'mov', 'avi', 'webm'] },
      { name: 'Documents', extensions: ['pdf', 'doc', 'docx', 'txt', 'md', 'rtf'] },
      { name: 'Spreadsheets', extensions: ['xlsx', 'xls', 'csv', 'tsv'] },
      { name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'svg'] },
      { name: 'Audio', extensions: ['mp3', 'wav', 'ogg', 'm4a'] },
      { name: 'Video', extensions: ['mp4', 'mov', 'avi', 'webm'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });
  
  return result.filePaths;
});

ipcMain.handle('select-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  });
  
  return result.filePaths[0];
});

ipcMain.handle('select-folder-files', async () => {
  const fs = require('fs').promises;
  
  console.log('select-folder-files handler called');
  
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Select folder to upload all files'
  });
  
  console.log('Dialog result:', result);
  
  if (result.canceled || !result.filePaths[0]) {
    console.log('Dialog was canceled or no folder selected');
    return null;
  }
  
  const folderPath = result.filePaths[0];
  
  // Recursively find all files in the folder
  async function getAllFiles(dirPath, filesList = []) {
    const files = await fs.readdir(dirPath);
    
    for (const file of files) {
      const filePath = path.join(dirPath, file);
      const stat = await fs.stat(filePath);
      
      if (stat.isDirectory()) {
        // Skip hidden directories and common ignore patterns
        if (!file.startsWith('.') && file !== 'node_modules' && file !== '__pycache__') {
          await getAllFiles(filePath, filesList);
        }
      } else {
        // Only include files with common document extensions
        const ext = path.extname(file).toLowerCase();
        const supportedExts = [
          // Documents
          '.pdf', '.doc', '.docx', '.txt', '.md', '.rtf',
          // Spreadsheets - NEW
          '.xlsx', '.xls', '.csv', '.tsv',
          // Images
          '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg',
          // Audio
          '.mp3', '.wav', '.ogg', '.m4a',
          // Video
          '.mp4', '.mov', '.avi', '.webm'
        ];
        
        if (supportedExts.includes(ext)) {
          filesList.push(filePath);
        }
      }
    }
    
    return filesList;
  }
  
  try {
    const allFiles = await getAllFiles(folderPath);
    return {
      folderPath,
      files: allFiles,
      fileCount: allFiles.length
    };
  } catch (error) {
    console.error('Error reading folder:', error);
    return null;
  }
});

ipcMain.handle('show-in-folder', async (event, filePath) => {
  shell.showItemInFolder(filePath);
});

ipcMain.handle('open-external', async (event, url) => {
  shell.openExternal(url);
});

// Prevent new window creation
app.on('web-contents-created', (event, contents) => {
  contents.on('new-window', (navigationEvent, navigationUrl) => {
    navigationEvent.preventDefault();
    shell.openExternal(navigationUrl);
  });
});