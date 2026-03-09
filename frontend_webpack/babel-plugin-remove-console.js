// Babel plugin to remove console.logs in production
module.exports = function ({ types: t }) {
  return {
    name: "remove-console",
    visitor: {
      CallExpression(path, state) {
        const callee = path.get("callee");
        
        if (!callee.isMemberExpression()) return;

        if (isIncludedConsoleCall(callee, state.opts.exclude)) {
          path.remove();
        }
      }
    }
  };
};

function isIncludedConsoleCall(callee, excludeArray = []) {
  const object = callee.get("object");
  const property = callee.get("property");

  if (!object.isIdentifier({ name: "console" })) {
    return false;
  }

  const propertyName = property.node.name;
  
  // Keep console.error and console.warn by default, remove console.log
  const defaultExclude = ["error", "warn"];
  const exclude = excludeArray.length > 0 ? excludeArray : defaultExclude;

  return !exclude.includes(propertyName);
}
