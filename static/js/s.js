const {createApp} = Vue;

createApp({
    data() {
        return {
            posts: initPosts,
            answer: '',
            results: []
        }
    },
    methods: {
        downloadSelectedImages() {
            window.alert("You've been pranked! The download doesn't work today");
        },
        submit_answer() {
            console.log(answer);
        }
    },

}).mount('#app');
