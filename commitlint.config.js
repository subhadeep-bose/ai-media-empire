module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'refactor', 'test', 'ci', 'docs', 'chore'],
    ],
    'subject-case': [0],  // disabled — abbreviations (TTS, SRT, AI, LLM) are valid
    'subject-max-length': [2, 'always', 100],
    'body-max-line-length': [0],   // allow long Co-Authored-By lines
    'footer-max-line-length': [0],
  },
};
