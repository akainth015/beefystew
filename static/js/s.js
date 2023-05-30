const {createApp} = Vue;

createApp({
    data() {
        return {
            posts: initPosts,
        }
    },
    methods: {
        downloadSelectedImages() {
            window.alert("You've been pranked! The download doesn't work today");
        }
    }
}).mount('#app');
