const path = require('path');

module.exports = {
    mode: 'production',
    entry: {
        index: path.resolve(__dirname, 'src/js/index.js'),
        branches: path.resolve(__dirname, 'src/js/branches.js'),
        project: path.resolve(__dirname, 'src/js/project.js'),
        pr: path.resolve(__dirname, 'src/js/pr.js'),
    },
    output: {
        filename: '[name].bundle.js',
        path: path.resolve(__dirname, 'dist/js'),
        clean: true
    },
};