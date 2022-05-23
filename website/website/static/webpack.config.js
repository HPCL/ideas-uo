module.exports = {
    mode: 'production',
    entry: {
        index: './src/index.js',
        branches: './src/branches.js',
        project: './src/project.js',
        pr: './src/pr.js'
    },
    output: {
        filename: '[name].[contenthash].bundle.js'
    },
    module: {
        rules: [
            {
                test: /\.css$/i,
                use: ['style-loader', 'css-loader'],
            },
        ],
    },
};