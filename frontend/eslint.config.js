import path from "node:path";
import js from "@eslint/js";
import { defineConfig } from "eslint/config";
import prettier from "eslint-config-prettier";
import importPlugin from "eslint-plugin-import";
import jsxA11y from "eslint-plugin-jsx-a11y";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import { configs as tseslintConfigs } from "typescript-eslint";

// Line limits count physical lines (blanks and comments included), like the Python file-length check.
const MAX_FILE_LINES = 250;
const MAX_COMPONENT_FILE_LINES = 150;
const MAX_FUNCTION_LINES = 40;
const MAX_COMPLEXITY = 8;
const MAX_PARAMS = 4;
const MAX_DEPTH = 3;

const FEATURES = ["dashboard", "widgets", "datasets"];
const FEATURE_MESSAGE = "Import a feature through its index.ts";

// Layers run app -> pages -> features -> shared; a layer never imports from one above it.
const layerZones = [
  { target: "./src/shared", from: ["./src/features", "./src/pages", "./src/app"] },
  { target: "./src/features", from: ["./src/pages", "./src/app"] },
  { target: "./src/pages", from: "./src/app" },
];

// Relative imports can bypass the alias pattern below, so each feature also guards its own folder.
const featureZones = FEATURES.map((feature) => ({
  target: ["./src/!(features)/**/*", `./src/features/!(${feature})/**/*`],
  from: `./src/features/${feature}`,
  except: ["./index.ts"],
  message: FEATURE_MESSAGE,
}));

const baseZones = [...layerZones, ...featureZones];
const testSupportZone = {
  target: "./src",
  from: "./src/test",
  message: "Test helpers may only be imported from test files",
};

const restrictedReactImports = {
  name: "react",
  importNames: ["FC", "FunctionComponent"],
  message: "Type props with `type` and a plain function instead of React.FC",
};
const restrictedReactFcSelector = {
  selector:
    "TSTypeReference > TSQualifiedName[left.name='React'][right.name=/^(FC|FunctionComponent)$/]",
  message: "Type props with `type` and a plain function instead of React.FC",
};

export default defineConfig({
  basePath: import.meta.dirname,
  extends: [
    {
      ignores: [
        "dist",
        "coverage",
        "playwright-report",
        "test-results",
        "src/shared/api/schema.d.ts",
      ],
    },
    js.configs.recommended,
    tseslintConfigs.strictTypeChecked,
    tseslintConfigs.stylisticTypeChecked,
    react.configs.flat.recommended,
    react.configs.flat["jsx-runtime"],
    jsxA11y.flatConfigs.recommended,
    importPlugin.flatConfigs.recommended,
    importPlugin.flatConfigs.typescript,
    {
      languageOptions: {
        parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
      },
      settings: {
        react: { version: "detect" },
        "import/internal-regex": "^@/",
        "import/resolver": {
          typescript: { project: path.join(import.meta.dirname, "tsconfig.json") },
        },
      },
      plugins: { "react-hooks": reactHooks },
      rules: {
        ...reactHooks.configs.recommended.rules,
        "max-lines": ["error", { max: MAX_FILE_LINES }],
        "max-lines-per-function": ["error", { max: MAX_FUNCTION_LINES }],
        complexity: ["error", MAX_COMPLEXITY],
        "max-params": ["error", MAX_PARAMS],
        "max-depth": ["error", MAX_DEPTH],
        "no-console": "error",
        "@typescript-eslint/no-explicit-any": "error",
        "@typescript-eslint/consistent-type-definitions": ["error", "type"],
        "import/no-cycle": "error",
        "import/order": [
          "error",
          {
            groups: ["builtin", "external", "internal", ["parent", "sibling", "index"]],
            alphabetize: { order: "asc" },
            "newlines-between": "never",
          },
        ],
        "import/no-restricted-paths": [
          "error",
          { basePath: import.meta.dirname, zones: baseZones },
        ],
        "no-restricted-imports": [
          "error",
          {
            paths: [restrictedReactImports],
            patterns: [{ group: ["@/features/*/*"], message: FEATURE_MESSAGE }],
          },
        ],
        "no-restricted-syntax": ["error", restrictedReactFcSelector],
      },
    },
    {
      files: ["src/**/*.{ts,tsx}"],
      languageOptions: { globals: globals.browser },
    },
    {
      files: ["*.{js,ts}", "e2e/**/*.ts"],
      languageOptions: { globals: globals.node },
    },
    {
      files: ["src/**/*.{ts,tsx}"],
      ignores: ["**/*.test.{ts,tsx}", "src/test/**"],
      rules: {
        "import/no-restricted-paths": [
          "error",
          { basePath: import.meta.dirname, zones: [...baseZones, testSupportZone] },
        ],
      },
    },
    {
      files: ["**/*.tsx"],
      rules: { "max-lines": ["error", { max: MAX_COMPONENT_FILE_LINES }] },
    },
    {
      files: ["**/*.test.{ts,tsx}", "src/test/**"],
      rules: { "max-lines-per-function": "off" },
    },
    {
      files: ["**/*.js"],
      ...tseslintConfigs.disableTypeChecked,
    },
    prettier,
  ],
});
