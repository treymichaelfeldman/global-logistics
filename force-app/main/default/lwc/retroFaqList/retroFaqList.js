import { LightningElement, track } from 'lwc';

export default class RetroFaqList extends LightningElement {
    @track faqs = [
        {
            id: '1',
            question: 'How do I track my package?',
            answer: 'Our online tracking system is currently under construction. For immediate assistance, please use your telephone!',
            answerClass: 'faq-answer hidden'
        },
        {
            id: '2',
            question: 'What are your rates?',
            answer: 'Rates change daily based on gas prices. The only way to get an accurate quote is to speak to a representative.',
            answerClass: 'faq-answer hidden'
        },
        {
            id: '3',
            question: 'Do you ship internationally?',
            answer: 'Yes! We ship all over the globe. We have the best routing tables in the business.',
            answerClass: 'faq-answer hidden'
        }
    ];

    toggleFaq(event) {
        const id = event.currentTarget.dataset.id;
        this.faqs = this.faqs.map(faq => {
            if (faq.id === id) {
                const isHidden = faq.answerClass.includes('hidden');
                return { ...faq, answerClass: isHidden ? 'faq-answer visible' : 'faq-answer hidden' };
            }
            return faq;
        });
    }

    handleCall() {
        alert('Dialing 1-800-GLOBAL-99...');
    }
}