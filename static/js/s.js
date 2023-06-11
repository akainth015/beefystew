const {createApp} = Vue;

createApp({
    data() {
        return {
            index: 1,
            answer: '',
            results: [],
            posts: initPosts
        }
    },
    methods: {
        downloadSelectedImages() {
            window.alert("You've been pranked! The download doesn't work today");
        },
        submit_answer() {
            (this.results).push({index: this.index, answer: this.answer});
            console.log(this.results);
            this.index = this.index + 1;
        }
    },

}).mount('#app');
