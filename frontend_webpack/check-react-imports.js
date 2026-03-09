const fs = require('fs');
const path = require('path');

function checkReactImports(dir) {
  const files = fs.readdirSync(dir, { withFileTypes: true });
  
  files.forEach(file => {
    const fullPath = path.join(dir, file.name);
    
    if (file.isDirectory()) {
      checkReactImports(fullPath);
    } else if (file.name.endsWith('.js') || file.name.endsWith('.jsx')) {
      const content = fs.readFileSync(fullPath, 'utf8');
      const hasJsx = /<[A-Za-z]/.test(content);
      const hasReactApi = /(React\.[A-Za-z]|lazy\(|Suspense|Fragment|useState|useEffect|useContext|useReducer|useCallback|useMemo|useRef|useImperativeHandle|useLayoutEffect|useDebugValue)/.test(content);
      
      if ((hasJsx || hasReactApi) && !/import\s+React\b/.test(content)) {
        console.log(`Missing React import in: ${fullPath}`);
      }
    }
  });
}

checkReactImports(path.join(__dirname, 'src'));
